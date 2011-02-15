# -*- Mode:Python; coding: utf-8 -*-

import nodes
import graph
import sys
from itypes import *

from pprint import pprint as pp
from pdb import set_trace as trace

is_a = isinstance

# The 'subst', or type substitution/map, is not an actual data structure,
#   but rather lives in the '.val' attribute of the set of all type variables.
# To 'apply the subst', simply follow the path through each type variable
#   until you get to something that's not a tvar.

# this is now only applied *after* unification.

def apply_subst_to_type (t):

    # Another task performed here: the detection of recursive types.
    # This is done by adding a notation to a tvar before recursing
    # into it.  When we detect a cycle, we create a new moo_var, and
    # at the appropriate place create a 'moo' predicate binding the
    # variable.

    def p (t):
        if is_a (t, str):
            # rlabel predicate does this
            return t
        # equivalence class
        t = t.find()
        if t.pending:
            t.mv = t_var()
            return t.mv
        else:
            # replace all known tvars in <t>
            if is_a (t, t_predicate):
                if t.name == 'moo':
                    # we've already been here!
                    return t
                else:
                    t.pending = True
                    r = t_predicate (t.name, [p(x) for x in t.args])
                    t.pending = False
                    if t.mv:
                        r = moo (t.mv, r)
                        return r
                    else:
                        return r
            else:
                return t

    return p (t)

# http://en.wikipedia.org/wiki/Disjoint-set_data_structure
# this is Huet's algorithm
# See Kevin Knight: "Unification: A multidisciplinary survey (1989)"

glork = False
def unify (t0, t1):
    if glork:
        print t0, t1
    u = t0.find()
    v = t1.find()
    if u != v:
        if is_a (u, t_base) and is_a (v, t_base):
            raise TypeError ((u, v))
        # XXX unification would be simpler if all base types were done as no-arg predicates.
        elif is_a (u, t_base) and is_a (v, t_predicate):
            raise TypeError ((u, v))
        elif is_a (u, t_predicate) and is_a (v, t_base):
            raise TypeError ((u, v))            
        elif is_a (u, t_var) or is_a (v, t_var):
            pass
        elif is_pred (u, 'moo') and is_pred (v, 'moo'):
            pass
        elif is_pred (u, 'moo') or is_pred (v, 'moo'):
            # note early exit...
            return unify_moo (u, v)
        elif is_pred (u, 'rlabel', 'rdefault') or is_pred (v, 'rlabel', 'rdefault'):
            # note early exit...
            return unify_rows (u, v)
        elif is_a (u, t_predicate) and is_a (v, t_predicate) and (u.name != v.name or len (u.args) != len (v.args)):
            raise TypeError ((u, v))
        u.union (v)
        if is_a (u, t_predicate) and is_a (v, t_predicate):
            for i in range (len (u.args)):
                unify (u.args[i], v.args[i])
        else:
            pass

# This implementation of rows is based on the one in ATTPL, all of which are based on Rémy's
#  addition of pre() and abs() predicates to Wand's formulation.  See section 10.8 of ATTPL,
#  or "Type Inference for Records in a Natural Extension of ML" by Rémy.

def unify_rows (ty0, ty1):
    if is_pred (ty0, 'rlabel') and is_pred (ty1, 'rlabel'):
        if ty0.args[0] != ty1.args[0]:
            # distinct head labels, C-MUTATE-LL
            l0, t0, d0 = ty0.args
            l1, t1, d1 = ty1.args
            x = t_var()
            unify (d0, rlabel (l1, t1, x))
            unify (d1, rlabel (l0, t0, x))
        else:
            l0, t0, d0 = ty0.args
            l1, t1, d1 = ty1.args
            unify (t0, t1)
            unify (d0, d1)
    elif is_pred (ty0, 'rlabel') or is_pred (ty1, 'rlabel'):
        # only one is an rlabel
        if is_pred (ty1, 'rlabel'):
            # ensure that ty0 is the rlabel
            ty0, ty1 = ty1, ty0
        if is_pred (ty1, 'rdefault'):
            # C-MUTATE-DL
            x = ty1.args[0]
            unify (x, ty0.args[1])
            unify (ty1, ty0.args[2])
        elif is_a (ty1, t_predicate):
            # some other predicate
            # S-MUTATE-GL
            n = len (ty1.args)
            tvars0 = [t_var() for x in ty1.args]
            tvars1 = [t_var() for x in ty1.args]
            l0, t0, d0 = ty0.args
            g = ty1.name
            unify (t_predicate (g, tvars0), t0)
            unify (t_predicate (g, tvars1), d0)
            for i in range (n):
                unify (ty1.args[i], rlabel (l0, tvars0[i], tvars1[i]))
        else:
            raise TypeError ((ty0, ty1))
    elif is_pred (ty0, 'rdefault',) or is_pred (ty1, 'rdefault'):
        if is_pred (ty1, 'rdefault'):
            # ensure that ty0 is the rdefault/δ
            ty0, ty1 = ty1, ty0
        if is_pred (ty1, 'rdefault'):
            # they're both rdefault - normal decompose here
            assert (len(ty0.args) == 1 and len(ty1.args) == 1)
            # usually rdefault(abs) == rdefault(abs)
            unify (ty0.args[0], ty1.args[0])
        elif is_a (ty1, t_predicate):
            # some other predicate, S-MUTATE-GD
            n = len (ty1.args)
            g = ty1.name
            tvars = [ t_var() for x in ty1.args ]
            unify (ty0.args[0], t_predicate (g, tvars))
            for i in range (n):
                unify (ty1.args[i], rdefault (tvars[i]))
        else:
            raise TypeError ((ty0, ty1))
    else:
        raise TypeError ((ty0, ty1))

# XXX TODO: verify that all recursive types go through a row type.
# XXX can I be simplified?
def unify_moo (t0, t1):
    if is_pred (t1, 'moo'):
        # swap so t0 is always the moo
        t1, t0 = t0, t1
    # is this enough?
    unify (t0.args[0], t1)

def occurs_in_type (tvar, type):
    for t in walk_type (type):
        if tvar == t:
            return True
    else:
        return False

# XXX apparently this is done differently in many implementations,
#   somehow passing a depth argument around the type_of() functions
#   makes this easier?
def occurs_free_in_tenv (tvar, tenv):
    while tenv:
        rib, tenv = tenv
        for var, type in rib:
            if is_a (type, forall) and tvar in type.gens:
                # skip it if it's shadowed (should never happen...)
                pass
            elif occurs_in_type (tvar, type):
                return True
    return False

# if a node has user-supplied type, use it.  otherwise
#   treat it as a type variable.
# XXX untested in this new solver.
def optional_type (exp, tenv):
    if exp.type:
        return exp.type
    else:
        return t_var()

class forall:
    def __init__ (self, gens, type):
        self.gens = gens
        self.type = type

    def __repr__ (self):
        return '<forall %r %r>' % (self.gens, self.type)

def build_type_scheme (type, tenv, name):
    
    gens = set()

    def list_generic_tvars (t):
        if is_a (t, t_var):
            if not occurs_free_in_tenv (t, tenv):
                gens.add (t)
        elif is_pred (t, 'moo'):
            list_generic_tvars (t.args[1])
        elif is_a (t, t_predicate):
            for arg in t.args:
                list_generic_tvars (arg)
        elif is_a (t, t_base):
            pass
        elif is_a (t, str):
            pass
        elif is_a (t, moo_var):
            list_generic_tvars (t.tvar)
        else:
            raise ValueError

    type = apply_subst_to_type (type)
    list_generic_tvars (type)

    if not gens:
        return type
    else:
        return forall (gens, type)

def instantiate_type (type, tvar, fresh_tvar):
    def f (t):
        if is_a (t, t_var) or is_a (t, int):
            if t == tvar:
                return fresh_tvar
            else:
                return t
        elif is_a (t, t_predicate):
            return t_predicate (t.name, [f(x) for x in t.args])
        else:
            return t
    return f (type)

def instantiate_type_scheme (tscheme):
    gens = tscheme.gens
    body = tscheme.type
    for gen in gens:
        # ah, it's just repeatedly substituting...
        body = instantiate_type (body, gen, t_var())
    return body

def apply_tenv (tenv, name):

    def inst (t):
        if is_a (t, forall):
            return instantiate_type_scheme (t)
        else:
            return t

    while tenv:
        rib, tenv = tenv
        # walk the rib backwards for the sake of let*
        for i in range (len(rib)-1, -1, -1):
            var, type = rib[i]
            if var == name:
                # is this a type scheme?
                return inst (type)

    raise ValueError (name)

class UnboundVariable (Exception):
    pass

class typer:

    def __init__ (self, context):
        self.context = context
        self.verbose = self.context.verbose

    def go (self, exp):
        self.exp = exp
        tenv = (self.initial_type_environment(), None)
        try:
            result = self.type_of (exp, tenv)
        except TypeError:
            sys.exit (1)
        for node in exp:
            if node.type:
                if not hasattr (node.type, 'final'):
                    # cache
                    node.type.final = apply_subst_to_type (node.type)
                node.type = node.type.final
        if self.verbose or self.context.print_types:
            for n in exp:
                if n.is_a ('function'):
                    print n.name, n.type
        return result
        
    def initial_type_environment (self):
        constructors = []
        if False:
            for name, dt in self.context.datatypes.iteritems():
                poly_dt = build_type_scheme (dt, None, name)
                # store this type scheme in the type map
                the_type_map[name] = poly_dt
                for name in dt.get_datatype_constructors():
                    constructors.append ((name, poly_dt))
        return constructors

    def unify (self, t0, t1, tenv, exp):
        try:
            return unify (t0, t1)
        except TypeError as terr:
            self.print_type_error (exp, terr)

    def print_type_error (self, exp, terr):
        t0, t1 = terr.args[0]
        W = sys.stderr.write

        W ('\n---------------\nType Error:\n')
        W ('  t0: %r\n' % (t0,))
        W ('  t1: %r\n' % (t1,))
        W ('\nnear:\n')

        # find the portion of the program
        all = []
        def walk_depth (n, d):
            all.append ((n, d))
            for sub in n.subs:
                walk_depth (sub, d+1)

        walk_depth (self.exp, 0)

        # XXX this capability needs to be outside this file
        def near (n):
            lines = self.context.type_error_lines
            # we want <lines> before and after
            total = len (all)
            start = 0
            end   = total
            for i in range (total):
                if all[i][0] is n:
                    start = max (i-lines, start)
                    end   = min (i+lines, end)
                    break
            for ni, depth in all[start:end]:
                if ni is n:
                    indent = '--'
                else:
                    indent = '  '
                W ('%s%r\n' % (indent * depth, ni))

        near (exp)
        raise

    def type_of (self, exp, tenv):
        kind = exp.kind
        method = getattr (self, 'type_of_%s' % (kind,))
        exp.type = method (exp, tenv)
        return exp.type

    def type_of_literal (self, exp, tenv):
        return base_types[exp.ltype]

    def type_of_constructed (self, exp, tenv):
        return self.type_of (exp.value, tenv)

    def type_of_cexp (self, exp, tenv):
        tvars, sig = exp.type_sig
        scheme = forall (tvars, sig)
        sig = instantiate_type_scheme (scheme)
        if is_pred (sig, 'arrow'):
            result_type = sig.args[0]
            arg_types = sig.args[1:]
            for i in range (len (arg_types)):
                arg_type = arg_types[i]
                arg = exp.args[i]
                if is_pred (arg_type, 'raw'):
                    # hack: magically hide the 'raw' predicate
                    arg_type = arg_type.args[0]
                ta = self.type_of (arg, tenv)
                self.unify (ta, arg_type, tenv, arg)
            return result_type
        else:
            return sig

    def type_of_conditional (self, exp, tenv):
        t1 = self.type_of (exp.test_exp, tenv)
        self.unify (t1, t_predicate ('bool', ()), tenv, exp.test_exp)
        t2 = self.type_of (exp.then_exp, tenv)
        t3 = self.type_of (exp.else_exp, tenv)
        self.unify (t2, t3, tenv, exp)
        return t2

    def type_of_let_splat (self, exp, tenv):
        n = len (exp.inits)
        for i in range (n):
            init = exp.inits[i]
            name = exp.names[i]
            ta = self.type_of (init, tenv)
            # user-supplied type
            if name.type is not None:
                self.unify (ta, name.type, tenv, exp)
            tenv = ([(name.name, ta)], tenv)
        return self.type_of (exp.body, tenv)

    def type_of_function (self, exp, tenv):
        type_rib = []
        arg_types = []
        for formal in exp.formals:
            t = optional_type (formal, tenv)
            arg_types.append (t)
            type_rib.append ((formal.name, t))
        body_type = self.type_of (exp.body, (type_rib, tenv))
        r = arrow (body_type, *arg_types)
        # useful during complex type debugging
        #if exp.name:
        #    print exp.name, apply_subst_to_type (r)
        return r

    def type_of_application (self, exp, tenv):
        n = len (exp.rands)
        rator = exp.rator
        rator_type = self.type_of (exp.rator, tenv)
        # normal application
        arg_types = []
        for i in range (n):
            ta = self.type_of (exp.rands[i], tenv)
            arg_types.append (ta)
        result_type = t_var() # new type variable
        self.unify (rator_type, arrow (result_type, *arg_types), tenv, exp)
        return result_type

    def type_of_varref (self, exp, tenv):
        r = apply_tenv (tenv, exp.name)
        return r

    def type_of_varset (self, exp, tenv):
        # XXX implement the no-generalize rule for vars that are assigned.
        t1 = apply_tenv (tenv, exp.name)
        t2 = self.type_of (exp.value, tenv)
        self.unify (t1, t2, tenv, exp.value)
        return t_undefined()

    def type_of_sequence (self, exp, tenv):
        for sub in exp.subs[:-1]:
            # everything but the last, type it as don't-care
            ti = self.type_of (sub, tenv)
        return self.type_of (exp.subs[-1], tenv)

    def type_of_primapp (self, exp, tenv):
        # look it up in the environment.
        scheme = self.lookup_special_names (exp.name, exp.name_params)
        sig = instantiate_type_scheme (scheme)
        # XXX almost identical to type_of_cexp(), factor it out.
        result_type = sig.args[0]
        arg_types = sig.args[1:]
        for i in range (len (exp.args)):
            arg_type = arg_types[i]
            arg = exp.args[i]
            ta = self.type_of (arg, tenv)
            self.unify (ta, arg_type, tenv, arg)
        return result_type

    def lookup_special_names (self, name, params):
        if name == '%rmake':
            return forall ((), arrow (rproduct (rdefault (abs()))))
        elif name.startswith ('%rextend/'):
            what, label = name.split ('/')
            # ∀XYZ.(Π(l:X;Y), Z) → Π(l:pre(Z);Y)
            return forall (
                (0,1,2),
                arrow (
                    rproduct (rlabel (label, pre(2), 1)),
                    rproduct (rlabel (label, 0, 1)),
                    2
                    )
                )
        elif name.startswith ('%raccess/'):
            what, label = name.split ('/')
            # ∀XY.Π(l:pre(X);Y) → X
            return forall ((0,1), arrow (0, rproduct (rlabel (label, pre(0), 1))))
        elif name.startswith ('%rset/'):
            what, label = name.split ('/')
            # ∀XY.(Π(l:pre(X);Y), X) → undefined
            return forall ((0,1), arrow (t_undefined(), rproduct (rlabel (label, pre(0), 1)), 0))
        elif name == '%vfail':
            return forall ((0,), arrow (0, rsum (rdefault (abs()))))
        elif name.startswith ('%dtcon/'):
            # lookup the type of the particular constructor
            what, dtname, label = name.split ('/')
            dt = self.context.datatypes[dtname]
            # e.g. list := nil | cons X list
            # %dtcon/list/cons := ∀X.(X,list(X)) → list(X)
            args = dt.constructors[label]
            return forall (dt.tvars, arrow (dt.scheme, *args))
        elif name.startswith ('%vcon/'):
            what, label, arity = name.split ('/')
            arity = int(arity)
            # remember each unique variant label
            self.remember_variant_label (label)
            if arity == 0:
                # ∀X.() → Σ(l:pre (Π());X)
                return forall ((1,), arrow (rsum (rlabel (label, pre (product()), 1))))
            elif arity == 1:
                # ∀XY.X → Σ(l:pre X;Y)
                return forall ((0,1), arrow (rsum (rlabel (label, pre(0), 1)), 0))
            else:
                # ∀ABCD.Π(A,B,C) → Σ(l:pre (Π(A,B,C));D)
                args = tuple(range (arity))
                return forall (range(arity+1), arrow (rsum (rlabel (label, pre (product(*args)), arity)), *args))
        elif name == '&vcase':
            label, arity = params
            # ∀012345.(3,4,5) → 0, Σ(l:1;2) → 0, Σ(l:pre(Π(3,4,5);2) → 0
            # ∀012345.f0,f1,s1 → 0
            args = range (3, arity+3)
            # success continuation
            f0 = arrow (0, *args)
            # failure continuation
            f1 = arrow (0, rsum (rlabel (label, 1, 2)))
            # the sum argument
            if arity == 1:
                t = args[0]
            else:
                t = product (*args)
            s1 = rsum (rlabel (label, pre (t), 2))
            return forall (range(arity+3), arrow (0, f0, f1, s1))
        elif name == '&vget':
            label, arity, index = params
            args = range (arity)
            rest = arity
            # e.g., to pick the second arg:
            # ∀0123. Σ(l:pre (0,1,2);3) → 1
            if arity > 1:
                vtype = rsum (rlabel (label, pre (product (*args)), rest))
            else:
                vtype = rsum (rlabel (label, pre (args[0]), rest))
            return forall (args + [arity], arrow (args[index], vtype))
        elif name.startswith ('%nvget/'):
            what, dtype, label, index = name.split ('/')
            dt = self.context.datatypes[dtype]
            ti = dt.constructors[label][int(index)]
            return forall (dt.tvars[:], arrow (ti, dt.scheme))
        elif name.startswith ('%vector-literal/'):
            what, arity = name.split ('/')
            arg_types = (0,) * int (arity)
            return forall ((0,), arrow (vector(0), *arg_types))
        elif name.startswith ('%make-vector'):
            return forall ((0,), arrow (vector(0), t_int(), 0))
        elif name.startswith ('%make-vec16'):
            return forall ((), arrow (vector(t_int16()), t_int()))
        elif name == '%%array-ref':
            return forall ((0,), arrow (0, vector (0), t_int()))
        elif name == '%%array-set':
            return forall ((0,), arrow (t_undefined(), vector (0), t_int(), 0))
        elif name == '%vec16-set':
            return forall ((), arrow (t_undefined(), vector(t_int16()), t_int(), t_int16()))
        elif name == '%vec16-ref':
            return forall ((), arrow (t_int16(), vector(t_int16()), t_int(), t_int16()))
        # ------
        # pattern matching
        # ------
        elif name == '%%match-error':
            return forall ((0,), arrow (0))
        elif name == '%%fatbar':
            return forall ((0,0), arrow (0, 0, 0))
        elif name == '%%fail':
            return forall ((0,), arrow (0))
        # -------
        elif name.count (':') == 1:
            # a constructor used in a 'constructed literal'
            dt, alt = name.split (':')
            return self.lookup_special_names ('%%dtcon/%s/%s' % (dt, alt))
        else:
            raise UnboundVariable (name)

    # XXX consider recording record labels at this point as well
    def remember_variant_label (self, label):
        vl = self.context.variant_labels
        if not vl.has_key (label):
            # adjust for the hacked pre-installed labels like 'cons' and 'nil'.
            vl[label] = len (vl)

    def type_of_fix (self, exp, tenv):
        # reorder fix into dependency order
        partition = graph.reorder_fix (exp, self.context.scc_graph)
        n = len (exp.inits)
        init_tvars = [None] * n
        init_types = [None] * n
        n2 = 0
        # new type var for each init (or user type)
        for i in range (n):
            if exp.names[i].type:
                # user-annotated type
                init_tvars[i] = exp.names[i].type
            else:
                init_tvars[i] = t_var()
        for part in partition:
            type_rib = []
            # build temp tenv for typing the inits
            for i in part:
                # for each function
                init = exp.inits[i]
                name = exp.names[i].name
                type_rib.append ((name, init_tvars[i]))
            temp_tenv = (type_rib, tenv)
            # type each init in temp_tenv
            for i in part:
                init = exp.inits[i]
                name = exp.names[i]
                ti = self.type_of (init, temp_tenv)
                self.unify (ti, init_tvars[i], temp_tenv, init)
                ti = apply_subst_to_type (ti)
                init_types[i] = ti
            # now extend the environment with type schemes instead
            type_rib = []
            for i in part:
                init = exp.inits[i]
                name = exp.names[i]
                tsi = build_type_scheme (init_types[i], tenv, name)
                type_rib.append ((name.name, tsi))
            # we now have a polymorphic environment for this subset
            tenv = (type_rib, tenv)
            n2 += len (type_rib)
        assert (n2 == n)
        # and type the body in that tenv
        return self.type_of (exp.body, tenv)

    def type_of_pvcase (self, exp, tenv):
        # (pvcase <alt_formals> <alt0> <alt1> ...)
        # each <alt> binds a separate set of variables (possibly empty)
        # the last alt binds against either "else" (not yet implemented),
        # or rdefault(abs()).
        alts = exp.alts[:]
        tv_exp = t_var()
        if len(alts) == len (exp.alt_formals):
            # no else clause, a closed sum type
            row = rdefault (abs())
        else:
            # with an else clause, open sum type
            row = t_var()
        for i in range (len (exp.alt_formals)):
            alt = alts[i]
            label, n, formals = exp.alt_formals[i]
            # row type extended with this label and its type
            args = [t_var() for x in range (n)]
            if len(args) == 1:
                row = rlabel (label, pre (args[0]), row)
            else:
                row = rlabel (label, pre(product (*args)), row)
            t_alt = self.type_of (alt, tenv)
            # each alt must have the same type
            self.unify (tv_exp, t_alt, tenv, exp)

        if len(alts) > len (exp.alt_formals):
            # an else clause
            self.unify (tv_exp, self.type_of (alts[-1], tenv), tenv, exp)
        # the value must have the row type determined
        #  by the set of polyvariant alternatives.
        t_val = self.type_of (exp.value, tenv)
        self.unify (rsum (row), t_val, tenv, exp)
        return t_alt

    def type_of_nvcase (self, exp, tenv):
        # (nvcase <vtype> <val> <alt0> <alt1> ...)
        # like a conditional, but with more branches.
        dt = self.context.datatypes[exp.vtype]
        t_val = self.type_of (exp.value, tenv)
        if len(dt.tvars):
            # it's a type scheme, instantiate it
            dt_type = instantiate_type_scheme (forall (dt.tvars, dt.scheme))
            self.unify (t_val, dt_type, tenv, exp)
        else:
            self.unify (t_val, dt.scheme, tenv, exp)
        # each alt has the same type
        tv_exp = t_var()
        for alt in exp.alts:
            self.unify (tv_exp, self.type_of (alt, tenv), tenv, exp)
        # this will work even when else_clause is a dummy %%match-error
        self.unify (tv_exp, self.type_of (exp.else_clause, tenv), tenv, exp)
        return tv_exp
        
        
    
