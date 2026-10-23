param([switch]$NoBrowser)
$ErrorActionPreference='Stop'
$taskRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'offline'))+[IO.Path]::DirectorySeparatorChar
if(!(Test-Path -LiteralPath (Join-Path $taskRoot 'offline-data.json'))){throw 'Estrai prima tutto il file ZIP in una cartella.'}
$taskListener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0)
$taskListener.Start()
$taskPort=$taskListener.LocalEndpoint.Port
$taskUrl="http://127.0.0.1:$taskPort/"
Write-Host 'Gestionale offline - SOLA CONSULTAZIONE. Nessun collegamento ai servizi online.'
Write-Host 'Lascia aperta questa finestra durante la consultazione. Chiudila per terminare.'
Write-Host $taskUrl
if(!$NoBrowser){Start-Process $taskUrl}
$taskMime=@{'.html'='text/html; charset=utf-8';'.js'='text/javascript';'.mjs'='text/javascript';'.css'='text/css';'.json'='application/json';'.wasm'='application/wasm';'.svg'='image/svg+xml';'.png'='image/png'}
try{while($true){
 $taskSocket=$taskListener.AcceptTcpClient()
 try{
  $taskStream=$taskSocket.GetStream();$taskStream.ReadTimeout=10000
  $taskReader=[IO.StreamReader]::new($taskStream,[Text.Encoding]::ASCII,$false,1024,$true)
  $taskRequest=$taskReader.ReadLine()
  if(!$taskRequest){continue}
  while($taskReader.ReadLine()){}
  $taskMatch=[regex]::Match($taskRequest,'^GET (/\S*) HTTP/1\.[01]$')
  $taskStatus='200 OK';$taskType='application/octet-stream';$taskBytes=[byte[]]@()
  if(!$taskMatch.Success){$taskStatus='405 Method Not Allowed'}else{
   $taskRelative=[Uri]::UnescapeDataString(($taskMatch.Groups[1].Value -split '\?')[0]).TrimStart('/')
   if(!$taskRelative){$taskRelative='index.html'}
   $taskPath=[IO.Path]::GetFullPath((Join-Path $taskRoot $taskRelative))
   if(!$taskPath.StartsWith($taskRoot,[StringComparison]::OrdinalIgnoreCase)){$taskStatus='403 Forbidden'}
   elseif(!(Test-Path -LiteralPath $taskPath -PathType Leaf)){$taskStatus='404 Not Found'}
   else{$taskBytes=[IO.File]::ReadAllBytes($taskPath);$taskExtension=[IO.Path]::GetExtension($taskPath);if($taskMime.ContainsKey($taskExtension)){$taskType=$taskMime[$taskExtension]}}
  }
  $taskHeader="HTTP/1.1 $taskStatus`r`nContent-Type: $taskType`r`nContent-Length: $($taskBytes.Length)`r`nConnection: close`r`nCache-Control: no-store`r`nX-Content-Type-Options: nosniff`r`nContent-Security-Policy: default-src 'self' blob: data:; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self'; worker-src 'self' blob:; style-src 'self' 'unsafe-inline'`r`n`r`n"
  $taskHeaderBytes=[Text.Encoding]::ASCII.GetBytes($taskHeader);$taskStream.Write($taskHeaderBytes,0,$taskHeaderBytes.Length);$taskStream.Write($taskBytes,0,$taskBytes.Length)
 }catch{Write-Verbose $_}finally{$taskSocket.Dispose()}
}}finally{$taskListener.Stop()}
