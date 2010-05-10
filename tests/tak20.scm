
(define (>= a b)
  (%%cexp (int int -> bool) "%s>=%s" a b))

(define (- a b)
  (%%cexp (int int -> int) "%s-%s" a b))

(define (zero? a)
  (%%cexp (int -> bool) "%s==0" a))

(define (tak x y z)
  (if (>= y x)
      z
      (tak (tak (- x 1) y z)
	   (tak (- y 1) z x)
	   (tak (- z 1) x y))))

(let loop ((n 20))
  (let ((r (tak 18 12 6)))
    (if (zero? n)
	r
	(loop (- n 1)))))
