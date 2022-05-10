if version < 600
    syntax clear
elseif exists("b:current_syntax")
    finish
endif

setlocal foldmethod=syntax

syntax case match

syntax match remyNotecardMarker #\v^NOTECARD\s+[-_a-zA-Z0-9]+# contained
syntax match remyNotecardLine #\v^NOTECARD\s+[-_a-zA-Z0-9]+(\s*[-_a-zA-Z0-9]+)*# contains=remyNotecardMarker

syntax match remyFieldLabel #\v^:[_a-zA-Z][_a-zA-Z0-9]*:#

"syn region remyNotecard start=#\v\zs^NOTECARD# end=#\v^NOTECARD|\%$# fold transparent
syn region remyNotecard start=#\v\zs^NOTECARD# end=#\v\ze^NOTECARD# fold transparent
 
highlight remyNotecardLine ctermfg=Red
highlight remyNotecardMarker cterm=bold ctermfg=Red

highlight remyFieldLabel cterm=bold ctermfg=Black

let b:current_syntax = "remy"

" vim: ts=8
