;; -*- Mode: Irken -*-

;; we can't use the one from lib/ctype.scm, it isn't
;;  expressive enough (yet).

;; C types consist of two morally different building blocks - types and
;; 'declarators'.  A declarator is simply a type with a name attached.
;; declarators are used in typedefs, struct/union elements, and
;; function parameters.

(datatype ctype2
  (:name symbol)   ;; void, thing_t, etc...
  (:int cint bool) ;; kind/size, signed?
  (:float bool bool) ;; long? double?
  (:array int ctype2)
  (:pointer ctype2)
  ;; XXX seriously consider collapsing this into a single alt
  ;;   with a boolean to indicate which kind.  would avoid much
  ;;   code duplication.
  (:struct symbol (maybe (list declarator)))
  (:union  symbol (maybe (list declarator)))
  (:function ctype2 (list declarator))
  )

;; a ctype in s-expression form.
(define ctype2-repr
  (ctype2:name 'void)   -> "void"
  (ctype2:name name)    -> (format "(type " (symbol->string name) ")")
  (ctype2:int cint s?)  -> (cint-repr cint s?)
  (ctype2:float l? d?)  -> (format (if l? "long" "") (if d? "double" "float"))
  (ctype2:array size t) -> (format "(array " (int size) " " (ctype2-repr t) ")")
  (ctype2:pointer t)    -> (format "(* " (ctype2-repr t) ")")
  (ctype2:struct name (maybe:no))        -> (format "(struct " (sym name) ")")
  (ctype2:struct name (maybe:yes slots)) -> (format "(struct " (sym name) " (" (join declarator-repr " " slots) "))")
  (ctype2:union name (maybe:no))         -> (format "(union " (sym name) ")")
  (ctype2:union name (maybe:yes slots))  -> (format "(union " (sym name) " (" (join declarator-repr " " slots) "))")
  (ctype2:function type args)            -> (format "(fun " (join declarator-repr " " args) " -> " (ctype2-repr type) ")")
  )

;; a 'declarator' is a combination of name and type.  sometimes the
;; name is not present (e.g. parameters in function declarations)
(datatype declarator
  (:t ctype2 (maybe symbol))
  )

(define declarator-repr
  (declarator:t type (maybe:no))
  -> (format (ctype2-repr type))
  (declarator:t type (maybe:yes name))
  -> (format "(named " (sym name) " " (ctype2-repr type) ")")
  )

;; ...and back into C

(define cint->c
  (cint:char)     -> "char"
  (cint:short)    -> "short"
  (cint:int)      -> "int"
  (cint:long)     -> "long"
  (cint:longlong) -> "long long"
  (cint:width w)  -> (format "int" (int (* w 8)) "_t")
  )

(define declarator->c
  ;; arrays and function pointers: special cases.
  (declarator:t (ctype2:array size t) (maybe:yes name))
  -> (format (ctype2->c t) " " (sym name) "[" (int size) "]")
  (declarator:t (ctype2:pointer (ctype2:function rtype args)) (maybe:yes name))
  -> (format (ctype2->c rtype) "(*" (sym name) ")(" (join declarator->c ", " args) ")")
  (declarator:t type (maybe:yes name))
  -> (format (ctype2->c type) " " (sym name))
  (declarator:t type (maybe:no))
  -> (ctype2->c type)
  )

(define ctype2->c
  (ctype2:name name)              -> (format (sym name))
  (ctype2:int cint s?)            -> (format (if s? "" "unsigned ") (cint->c cint))
  (ctype2:float l? d?)            -> (format (if l? "long " "") (if d? "double" "float"))
  (ctype2:array size t)           -> (format (ctype2->c t) (if (> size 0) (format "[" (int size) "]") "[]"))
  (ctype2:pointer t)              -> (format (ctype2->c t) "*")
  (ctype2:struct name (maybe:no)) -> (format "struct " (sym name))
  (ctype2:union name (maybe:no))  -> (format "union " (sym name))
  (ctype2:struct name (maybe:yes slots))
  -> (format "struct " (sym name) " {\n  " (join declarator->c ";\n  " slots) ";\n}")
  (ctype2:union name (maybe:yes slots))
  -> (format "union " (sym name) " {\n  " (join declarator->c ";\n  " slots) ";\n}")
  (ctype2:function rtype args) ;; unnamed function pointer.
  -> (format (ctype2->c rtype) "(*)(" (join declarator->c ", " args) ")")
  )

;; imperative walker: call <p> on all subtypes of <type>
;; note: walks from outside-in.
(define (walk-type p type)
  (define (W type)
    (p type)
    (match type with
      (ctype2:pointer sub)                -> (W sub)
      (ctype2:array _ sub)                -> (W sub)
      (ctype2:struct _ (maybe:yes slots)) -> (WD slots)
      (ctype2:union _ (maybe:yes slots))  -> (WD slots)
      (ctype2:function rtype args)        -> (begin (W rtype) (WD args))
      _ -> #u))
  (define (WD decls)
    (for-list decl decls
      (match decl with
        (declarator:t type name)
        -> (W type))))
  (W type)
  )

;; functional walker: run all subtypes through <p>
(define (map-type p type)
  (define (M type)
    (p (match type with
         (ctype2:pointer sub)                   -> (ctype2:pointer (M sub))
         (ctype2:array n sub)                   -> (ctype2:array n (M sub))
         (ctype2:struct name (maybe:yes slots)) -> (ctype2:struct name (maybe:yes (MD slots)))
         (ctype2:union name (maybe:yes slots))  -> (ctype2:union name (maybe:yes (MD slots)))
         (ctype2:function rtype args)           -> (ctype2:function (M rtype) (MD args))
         _                                      -> type)))
  (define (MD decls)
    (map (lambda (decl)
           (match decl with
             (declarator:t type name)
             -> (declarator:t (M type) name)))
         decls))
  (M type)
  )

;; functional walker: run all subtypes through <p>,
;;  which takes two arguments:
;;  1) the path of declarator names (list symbol)
;;  2) the type object.
;;
;; this is an instance of an interesting functional-programming
;;  pattern: most jobs can be done with 'downward' pattern matching,
;;  but sometimes you need pattern matching on the *parents* of an
;;  object as well.  in this case, we match on the declarator parent
;;  path.

(define (map-type-path p path type)
  (define (M path type)
    (p path
       (match type with
         (ctype2:pointer sub)                   -> (ctype2:pointer (M path sub))
         (ctype2:array n sub)                   -> (ctype2:array n (M path sub))
         (ctype2:struct name (maybe:yes slots)) -> (ctype2:struct name (maybe:yes (MD path slots)))
         (ctype2:union name (maybe:yes slots))  -> (ctype2:union name (maybe:yes (MD path slots)))
         (ctype2:function rtype args)           -> (ctype2:function (M path rtype) (MD path args))
         _                                      -> type)))
  ;; whenever we descend through a declarator, push that name onto the path.
  (define (MD path0 decls)
    (map (lambda (decl)
           (match decl with
             (declarator:t type (maybe:yes name))
             -> (declarator:t (M (list:cons name path) type) (maybe:yes name))
             (declarator:t type (maybe:no))
             -> (declarator:t (M path type) (maybe:no))
             ))
         decls))
  (M path type)
  )

