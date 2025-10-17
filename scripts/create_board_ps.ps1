$params = @{
    name = 'Sistema de Análises de CNPJ';
    defaultLists = 'true';
    prefs_permissionLevel = 'private';
    key = 'c47d879a1845f1d91bf11a5c03bc76f7';
    token = 'ATTAbfda1bde587c6e23e3883a89517c1b3029db705423f15d6f7358e22ff718e2fe0747AFD7'
}
$r = Invoke-RestMethod -Method Post -Uri 'https://api.trello.com/1/boards' -Body $params
$r | ConvertTo-Json -Depth 3 | Out-File -FilePath new_board.json -Encoding utf8
Write-Output "Created board saved to new_board.json"