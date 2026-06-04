// Copyright (c) Ivan Bondarev, Stanislav Mikhalkovich (for details please see \doc\copyright.txt)
// This code is distributed under the GNU LGPL (for details please see \doc\license.txt)
///--
unit __RedirectIOMode;

//------------------------------------------------------------------------------
// Модуль подключаемый в режиме запуска со связью с оболочкой                  
// (с) DarkStar 2007
// Функции:
//    1. Посылка в поток ErrorStream сигнала [READLNSIGNAL]
//    2. Перехват исключений по AppDomain.CurrentDomain.UnhandledException и 
//       передача их в поток ErrorStream
//    3. Перехват исключений по Application.ThreadException и 
//       передача их в поток ErrorStream  
//------------------------------------------------------------------------------

{$reference 'System.Windows.Forms.dll'}

interface

uses PABCSystem, System;

type
  __ReadSignalOISystem = class(IOStandardSystem)
  public
    function peek: integer; override;
    function read_symbol: char; override;
    function ReadLine: string; override;
    procedure writeln; override;
    procedure write(obj: object); override;
  end;

///--
procedure __InitModule__;

implementation

const
  RedirectIOModeArg = '[REDIRECTIOMODE]';
  RedirectIOModeNoWait = '[REDIRECTIOMODENOWAIT]';
  ReadlnSignalCommand = '[READLNSIGNAL]';
  CodePageCommandTemplate = '[CODEPAGE{0}]';
  RuntimeExceptionCommandTemplate = '[EXCEPTION]{0}[MESSAGE]{1}[STACK]{2}[END]';
  R = #10;
  N = #13;
  
var 
  ReadlnSignalSended := false;
  LastReadSymbol := #0;
  
procedure __ReadSignalOISystem.writeln;
begin
  inherited writeln;
  //Console.Write('[NEWLINE]');
end;
procedure __ReadSignalOISystem.write(obj: object);
begin
  inherited write(obj);
  Console.WriteLine('[FAKELINE]');
end;
  
procedure WriteToProcessErrorStream(text: string);
begin
  Console.Error.WriteLine(text);
  Console.Error.Flush;
end;

procedure SendReadlnRequest;
begin
  ReadlnSignalSended := true;
  //if not IsInputPipedOrRedirectedFromFile then
  WriteToProcessErrorStream(ReadlnSignalCommand);
end;

function __ReadSignalOISystem.peek: integer;
var i: integer;
begin
  if not ReadlnSignalSended then
    SendReadlnRequest;
  i := inherited peek;
  result := i;
end;

function __ReadSignalOISystem.read_symbol: char;
var c: char;
begin
  if not ReadlnSignalSended then
    SendReadlnRequest;
  c := inherited read_symbol;
  if {(LastReadSymbol=#13) and} (c=#10) then // Fix SSM 30.08.22 for Linux
    ReadlnSignalSended := false;  
  LastReadSymbol := c;
  result := c;
end;

function __ReadSignalOISystem.ReadLine: string; 
begin
  if not ReadlnSignalSended then
    SendReadlnRequest;
  var s := inherited ReadLine;
  ReadlnSignalSended := false;
  LastReadSymbol := R;
  Result := s;
end;

procedure SendExceptionToProcessErrorStream(e: Exception);
begin
  WriteToProcessErrorStream(
    string.Format(RuntimeExceptionCommandTemplate, e.GetType.ToString, e.Message, e.StackTrace));
end;

procedure DbgExceptionHandler(sender: object; args: UnhandledExceptionEventArgs);
var e: Exception;
begin
  e := Exception(args.ExceptionObject);
  if args.IsTerminating and (ExecuteBeforeProcessTerminateIn__Mode<>nil) then 
    ExecuteBeforeProcessTerminateIn__Mode(e);
  SendExceptionToProcessErrorStream(e);
  if args.IsTerminating then
    System.Diagnostics.Process.GetCurrentProcess.Kill;
end;

procedure Application_ThreadException(sender: object; args: System.Threading.ThreadExceptionEventArgs);
begin 
  SendExceptionToProcessErrorStream(args.Exception);
end;

var __initialized := false;

procedure AddThreadExceptionHandler;
begin
  System.Windows.Forms.Application.ThreadException += Application_ThreadException;
end;
procedure __InitModule;
begin
  try
    begin
        RedirectIOInDebugMode := true;
        //if IOStandardSystem(CurrentIOSystem).GetType = typeof(IOStandardSystem) then // SSM 30.04.06 - не менять! Влияет на PT4!
        CurrentIOSystem := new __ReadSignalOISystem;        
        //AppDomain.CurrentDomain.UnhandledException += DbgExceptionHandler;
        try
          AddThreadExceptionHandler;
        except
        end;
        
        Console.OutputEncoding := new System.Text.UTF8Encoding(false);
        Console.InputEncoding := new System.Text.UTF8Encoding(false);
    end;
  except
  end;
end;

procedure __InitModule__;
begin
  if not __initialized then
  begin
    __initialized := true;
    __InitPABCSystem;
    __InitModule;
  end;
end;

begin
  __InitModule__;
end.