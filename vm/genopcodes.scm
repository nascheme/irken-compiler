;; -*- Mode: Irken -*-

;; generate an include file for irkvm.c with information
;;  about all the opcodes.

(include "lib/basis.scm")
(include "lib/map.scm")
(include "self/byteops.scm")

(define (generate-irkvm-h)
  (let ((file (stdio/open-write "vm/irkvm.h"))
        (nops (vector-length opcode-info)))

    (define (W s)
      (stdio/write file s))

    (define (B b)
      (if b 1 0))

    (W (format
        "// generated by " sys.argv[0] " - do not edit\n\n"
        "typedef struct {\n"
        "  char * name;\n"
        "  int nargs;\n"
        "  int varargs;\n"
        "  int target;\n"
        "} opcode_info_t;\n\n"
        "opcode_info_t irk_opcodes[" (int nops) "] = {\n"
        ))

    (let ((lines '()))
      (for-range i (vector-length opcode-info)
        (let ((op opcode-info[i]))
          (push! lines
                (format
                 "  {"(rpad 15 "\"" (sym op.name) "\", ")
                 (int op.nargs) ", "
                 (int (B op.varargs)) ", "
                 (int (B op.target)) "}"))))
      (W (format (join ",\n" (reverse lines)))))
    (W "\n};\n")
    ;; emit symbolic names for each opcode.
    (for-range i (vector-length opcode-info)
      (let ((op opcode-info[i]))
        (W (format "#define IRK_OP_" (rpad 10 (upcase (symbol->string op.name)))
                   " " (int i) "\n"))))
    (W (format "#define IRK_NUM_OPCODES " (int nops) "\n"))
    (stdio/close file)
    ))

(generate-irkvm-h)
