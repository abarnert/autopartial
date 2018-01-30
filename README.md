# autopartial
Yet another Python lib for auto partial functions.

This project is meant for exploring the space, not to be a bulletproof
library for industrial use. There are multiple implementations, all of
which work, but with different limitations.

An auto partial function can be called as if it were curried (i.e.,
passing one argument at a time), or normally, or anywhere in between.
The actual call to the function implementation happens when the last
argument is passed in. Since this is just a wrapper around the stdlib
`functools.partial`, it handles most things the way you'd expect:

    >>> @autopartial
	... def f(a, b):
	...     return a+b
	>>> f
	autopartial(<function f at 0x1089ac130>)
	>>> f(1)
	autopartial(<function f at 0x1089ac130>, 1)
	>>> f(1)(2)
	3
    >>> @autopartial
	... def f(a, b, *, c):
	...     return a+b+c
	>>> f(1)(c=10)(2)
	13
	>>> inspect.signature(f(1))
	<Signature (b, *, c)>
    >>> @autopartial
	... def f(a, b=10, *, c):
	...     return a+b+c
	>>> f(1)(c=10)
	21

I don't know of any practical uses. Normally, you don't need fully
curries functions, and when you need `partial`, it's a single specific
partial application, so `autopartial` just means more keys to type and
less local visibility in the code. But maybe you just feel compelled
to make every language feel superficially more like Haskell in every
way possible?

# Implementations

All we need to do is inherit `partial` and then override the
`__call__` method: If we have the final arguments, just call our
`super`; if not, return a new `autopartial` binding the new arguments.

There's one big problem: How do we know whether we've got the final
argument(s) or not? There's no answer that's guaranteed to work
(besides making you duplicate the function's signature info in the
constructor). That's why there are multiple implementations.

Each implementation includes a short descriptive name for the
implementation, the name of the function actually exported, and a
performance cost.

The performance costs come from a microbenchmark (which you can
duplicate just by running the module yourself). In simplified
pseudocode:

    def f(a, b, *, c):
	    pass
	for each partialfunc:
        g = partialfunc(f) # nothing bound in
	    timeit(lambda: g(1, 2, c=3))

The results, normalized to just calling f, are:

    C partial      :   1.9
    Py partial     :   7.0
    dumb           :   5.1
	regexp         :  17
    signature      : 321
    cached _sig    :  57
    cached shortcut:  53
	
There is an extra tricky annoyance that we have to deal with: The
implementation of `partial.__new__` in `functools.py` is perfectly
capable of dealing with a subclass intelligently (or, in fact,
anything with an appropriate `func` attribute), but the implementation
of `partial_new` in `_functoolsmodule.c` requires that the type
matches exactly. This means that if you partial in multiple arguments
in separate calls, you end up with a wrapper around a wrapper around a
wrapper etc., with a correspondingly ugly `repr`, and a performance
hit on each partial or final call after the first.

The simplest way to handle this is to check the arguments to `__new__`
so we can manually unwrap a `partial` or subclass (including an
`autopartial`, of course) and call our super in a way that works for
both implementations.

As a minor additional problem (well, it might be major for some use
cases...), the `functools.py` implementation of `partial` is
picklable, but the `_functoolsmodule.c` is not. Making sure that
`autopartial` can be pickled if the underlying `partial` can is pretty
trivial. (Making it picklable no matter what would basically require
using the pure Python `partial`, with the corresponding 3x performance
cost, and the cost of not interacting properly with any actual
`_functools.partial` objects.)

## dumb (autopartial): 5.1x

This is the main version exported from the library. It always tries to
call the function, and rewraps instead if that call raises a
`TypeError`. That's dead simple, and fast, and for many use cases
it'll probably work fine.

However, the error handling leaves something to be desired. If you
call the wrapped function with too many arguments, or invalid keyword
arguments, or arguments of the wrong type, you won't get an exception;
it'll just wrap them up as more partial arguments to be passed to the
final call, which can never happen. (And of course if the function
implementation can itself raise `TypeError`...)

## regexp (not implemented): 17x

We could try to parse the `TypeError` and only wrap if it's caused by
too few arguments. At first glance, that seems easy. Any function
defined normally in Python, and any builtin using `argclinic`, is
going to give you one of these:

    TypeError: f() missing 1 required positional argument: 'b'
    TypeError: f() missing 1 required keyword-only argument: 'c'
	TypeError: Required argument 'number' (pos 1) not found

But what about builtins not using `argclinic`? Or third-party
extension modules? Or even pure-Python functions that parse `*args`?
You could try to match all of the common patterns in the stdlib and
major popular libraries, but there's a lot of them. There are endless
variations you'd have to parse, some of which require more logic than
you can cram in a regexp, like figuring out whether "expected exactly
one argument (3 given)" or "expected 1 or 2 arguments (0 given)" count
as too many or too few.

So, I gave up on this one after the first pass.

## signature (_autopartial2): 321x

Theoretically, you can't do any better than the dumb version without
sacrificing compatibility with some subset of Python. But practically,
the `inspect` module often does the right thing. It knows how to
construct a signature (including from a `partial`, and therefore from
an `autopartial`, and also from a wide variety of builtin and
extension functions) and try to bind arguments to it, and will raise a
nice and informative error if you can't.

If `bind` works, we've got a final call, so just call it (and let any
exception, including a `TypeError`, from the call pass through).

If `bind` raises but`bind_partial` works, we've got a new argument 
(or arguments), so just rewrap.

If both raise, the exception from `bind_partial` is exactly what the
caller probably wants.

There are some callables that `Signature` just can't handle--e.g.,
`ctypes` function pointers (even with `argtypes` defined). Those are
at least easy to deal with; you get an exception when trying to
construct the `autopartial`:

    >>> f = autopartial(ctypes.pythonapi.PyUnicode_New)
	ValueError: callable <_FuncPtr object at 0x1095dea70> is not supported by signature

More seriously, there are some callables that, as far as `Signature`
can tell, just take `*args, **kw`. This is the case for some C
extension functions, but also for many proxy functions created in pure
Python. For example, a dynamic ORM, bridge library, or remoting
library might just take `*args, **kw`, try it on the underlying
object, and only give you a `TypeError` if that fails. For such
functions, `autopartial` will appear to work, but if you try to
partially apply it, we'll think we have all the arguments and call the
actual function, raising a `TypeError`:

    >>> f = autopartial(proxy.files)
	>>> f(path)
	['.', '..']
	>>> f()
	TypeError: files requires 1 argument 'path'

Meanwhile, constructing a `Signature` object is very slow, and we're
doing this on every call. It adds a couple orders of magnitude to the
call overhead even for this trivial case:

    >>> @autopartial
	... def f():
	...     pass
	>>> f()

And if you're actually using it, it adds that overhead for each
partial application and the final one--e.g., we're doing it five times
in this example:

    >>> @autopartial
	... def g(a, b, c, d, e):
	...     pass
	>>> g(1)(2)(3)(4)(5)

## cached _sig (_autopartial3): 57x

If we cache the `Signature` for the original function, we can reuse it
for each call. Of course we're still constructing the `Signature`
once, so it doesn't make the trivial `f` case above any better. But
for the `g` example, if we're going to be constructing a lot of
partial functions out of `g`, constructing its `Signature` once, at
definition time, is no big deal.

This means we can no longer just pass the current arguments on to
`bind` and let the `partial`'s `Signature` do all the work, because we
only have the wrapped function's `Signature`. So we have to construct
the merged arguments that `partial` does to try to `bind` them. That's
not too hard, but it's not quite trivial (and it does make us brittle
against future changes in `partial`--if it doesn't construct the
arguments the same way we copied from CPython 3.6, we're testing the
wrong thing).

We can also no longer rely on `partial`'s constructor to flatten
everything for us; we need to manually copy over a cached `_sig` if
we're wrapping an already-wrapped function.

While the `bind` and `bind_partial` calls are a whole lot faster than
the initial construction, they're still not free. Each call is about
6x as fat as the simple `Signature` version, but that's still 10x as
slow as the dumb `TypeError` version. That may be acceptable in cases
where the function invocation time is swamped by the actual body (or
where function invocation is already very slow because, e.g., it's a
dynamic method generated by a remoting proxy), but it's still probably
too slow for general use.

## cached shortcut (_autopartial4): 53x

Once we're caching the `Signature` and constructing the final `bind`
arguments explicitly to be the exact same arguments that
`partial` is going to be constructing for the actual call, we can just
do that call ourselves and skip `partial`, rather than doing all the
same work twice.

But as you'd expect, optimizing out the fastest part of the call
overhead has little effect. And this is probably even more brittle.
