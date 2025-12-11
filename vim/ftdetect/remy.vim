" Vim file type detection for remy notecards
" Detects .ntc files and sets the filetype to 'remy'

autocmd BufRead,BufNewFile *.ntc setfiletype remy
