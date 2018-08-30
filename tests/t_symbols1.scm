(include "lib/core.scm")
(include "lib/pair.scm")
(include "lib/string.scm")
(include "lib/frb.scm")
(include "lib/symbol.scm")

(eq? 'thingy (string->symbol "thingy"))
(printn the-symbol-table)
(let ((s0 (string->symbol "abc"))
      (s1 (string->symbol "def"))
      )
  (printn (symbol->index 'thingy))
  (printn (symbol->index s0))
  (printn (symbol->index s1))
  (printn the-symbol-table)
  )

