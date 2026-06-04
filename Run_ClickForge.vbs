Set shell = CreateObject("WScript.Shell")
shell.Run "cmd /c ""cd /d """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & """ && Run_ClickForge.bat""", 0, False
