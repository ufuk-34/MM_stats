; Inno Setup kurulum betiği - Windows kurulum dosyası (DestekKayit-Kurulum.exe) üretir.
; Derleme: ISCC.exe /DAppVersion=1.0.0 packaging\installer.iss
; Önce PyInstaller ile dist\DestekKayit klasörü oluşturulmalıdır.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppName "Teknik Destek Kayıt Programı"
#define AppExe "DestekKayit.exe"

[Setup]
AppId={{6E4B7C1A-2F3D-4B8E-9C5A-7D1E3F2A4B6C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Kurum İçi Bilgi İşlem
; Program Files yerine C:\DestekKayit: veriler programın yanındaki "veri" klasöründe tutulur
DefaultDirName=C:\DestekKayit
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
PrivilegesRequired=admin
OutputDir=..\dist
OutputBaseFilename=DestekKayit-Kurulum
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
CloseApplications=yes

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstüne kısayol oluştur"
Name: "startup"; Description: "Windows açıldığında programı otomatik başlat"; Flags: unchecked

[Dirs]
; Personel bilgisayarı kullanırken de veritabanına yazılabilsin
Name: "{app}\veri"; Permissions: users-modify

[Files]
Source: "..\dist\DestekKayit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\KURULUM.md"; DestDir: "{app}"; DestName: "KULLANIM_KILAVUZU.txt"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\Teknik Destek Kayıt"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autoprograms}\Teknik Destek Kayıt\Teknik Destek Kayıt"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{autoprograms}\Teknik Destek Kayıt\Veri ve Yedek Klasörü"; Filename: "{app}\veri"
Name: "{autoprograms}\Teknik Destek Kayıt\Yönetici Şifresini Sıfırla"; Filename: "{app}\{#AppExe}"; Parameters: "--yonetici-sifirla"; WorkingDir: "{app}"
Name: "{autoprograms}\Teknik Destek Kayıt\Kullanım Kılavuzu"; Filename: "{app}\KULLANIM_KILAVUZU.txt"
Name: "{autostartup}\Teknik Destek Kayıt"; Filename: "{app}\{#AppExe}"; Parameters: "--no-browser"; WorkingDir: "{app}"; Flags: runminimized; Tasks: startup

[Run]
; Program yalnızca bu bilgisayarda çalışır; önceki sürümün açtığı güvenlik duvarı izni varsa kaldırılır
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Teknik Destek Kayit"""; Flags: runhidden
Filename: "{app}\{#AppExe}"; Description: "Programı şimdi başlat"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#AppExe}"; Flags: runhidden; RunOnceId: "StopApp"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Teknik Destek Kayit"""; Flags: runhidden; RunOnceId: "RemoveFirewallRule"

[Messages]
turkish.FinishedLabel=Kurulum tamamlandı. Program ilk açıldığında tarayıcıda "İlk Kurulum" ekranı gelir ve yönetici hesabı oluşturulur.%n%nKayıtlarınız program klasöründeki "veri" klasöründe tutulur; programı kaldırsanız bile bu klasör silinmez.

[Code]
// Güncelleme kurulumunda çalışan program kapatılır (dosyalar değiştirilebilsin)
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM {#AppExe}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := '';
end;
