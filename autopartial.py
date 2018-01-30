"""autopartial.py - functions with automatic partial application
"""

# Note that this module contains a number of implementations of the
# same idea. The one exported as autopartial is by far the simplest
# and most efficient, but it's not great for error checking. See
# the accompanying README.md for details.

import functools
import inspect

class autopartial(functools.partial):
    """New function with partial application of the given arguments
    and keywords, and automatic partial application when called with
    only some of the arguments. It can also be used as a decorator
    with no argument.
    """
    
    def __new__(cls, *args, **keywords):
        # See README.md for why we need this.
        if args and isinstance(args[0], functools.partial):
            func, *args = args
            args = func.args + tuple(args)
            tmpkw = func.keywords.copy()
            tmpkw.update(keywords)
            return super().__new__(cls, func.func, *args, **tmpkw)
        else:
            return super().__new__(cls, *args, **keywords)
    
    def __call__(self, *args, **keywords):
        # This assumes that TypeError is always caused by too
        # few arguments, which is of course not always true. See
        # README.me for details.
        try:
            return super().__call__(*args, **keywords)
        except TypeError:
            return type(self)(self, *args, **keywords)

class _autopartial2(functools.partial):
    """New function with partial application of the given arguments
    and keywords, and automatic partial application when called with
    only some of the arguments. It can also be used as a decorator
    with no argument.
    """

    def __new__(cls, *args, **keywords):
        # See README.md for why we need this.
        if args and isinstance(args[0], functools.partial):
            func, *args = args
            args = func.args + tuple(args)
            tmpkw = func.keywords.copy()
            tmpkw.update(keywords)
            return super().__new__(cls, func.func, *args, **tmpkw)
        else:
            return super().__new__(cls, *args, **keywords)
    
    def __call__(self, *args, **keywords):
        # See README.md for details on this implementation.
        sig = inspect.signature(self)
        try:
            sig.bind(*args, **keywords)
        except TypeError:
            sig.bind_partial(*args, **keywords)
            return type(self)(self, *args, **keywords)
        else:
            return super().__call__(*args, **keywords)

class _autopartial3(functools.partial):
    """New function with partial application of the given arguments
    and keywords, and automatic partial application when called with
    only some of the arguments. It can also be used as a decorator
    with no argument.
    """

    __slots__ = ('_sig',)

    def __new__(cls, *args, **keywords):
        # In addition to the usual reasons we need this (see
        # README.md), we also want to cache the Signature.
        if args and isinstance(args[0], functools.partial):
            func, *args = args
            args = func.args + tuple(args)
            tmpkw = func.keywords.copy()
            tmpkw.update(keywords)
            self = super().__new__(cls, func.func, *args, **tmpkw)
            try:
                self._sig = func._sig
            except AttributeError:
                self._sig = inspect.signature(self.func)
        else:
            self = super().__new__(cls, *args, **keywords)
            self._sig = inspect.signature(self.func)
        return self
    
    def __call__(self, *args, **keywords):
        # See README.md for details on this implementation.
        tmpargs = self.args + tuple(args)
        tmpkw = self.keywords.copy()
        tmpkw.update(keywords)
        try:
            self._sig.bind(*tmpargs, **tmpkw)
        except TypeError:
            self._sig.bind_partial(*tmpargs, **tmpkw)
            # TODO: Since we've done the work, reuse it here and
            # just construct from self.func, tmpargs, tmpkw?
            return type(self)(self, *args, **keywords)
        else:
            # TODO: Since we've done the work, reuse it here and
            # just call self.func(*tmpargs, **tmpkw)?
            return super().__call__(*args, **keywords)

class _autopartial4(functools.partial):
    """New function with partial application of the given arguments
    and keywords, and automatic partial application when called with
    only some of the arguments. It can also be used as a decorator
    with no argument.
    """

    __slots__ = ('_sig',)

    def __new__(cls, *args, **keywords):
        # In addition to the usual reasons we need this (see
        # README.md), we also want to cache the Signature.
        if args and isinstance(args[0], functools.partial):
            func, *args = args
            args = func.args + tuple(args)
            tmpkw = func.keywords.copy()
            tmpkw.update(keywords)
            self = super().__new__(cls, func.func, *args, **tmpkw)
            try:
                self._sig = func._sig
            except AttributeError:
                self._sig = inspect.signature(self.func)
        else:
            self = super().__new__(cls, *args, **keywords)
            self._sig = inspect.signature(self.func)
        return self
    
    def __call__(self, *args, **keywords):
        # See README.md for details on this implementation.
        tmpargs = self.args + tuple(args)
        tmpkw = self.keywords.copy()
        tmpkw.update(keywords)
        try:
            self._sig.bind(*tmpargs, **tmpkw)
        except TypeError:
            self._sig.bind_partial(*tmpargs, **tmpkw)
            return type(self)(self.func, *tmpargs, **tmpkw)
        else:
            return self.func(*tmpargs, **tmpkw)

def benchmark():
    import timeit
    from reprlib import recursive_repr

    class partial:
        """New function with partial application of the given arguments
        and keywords.
        """

        __slots__ = "func", "args", "keywords", "__dict__", "__weakref__"

        def __new__(*args, **keywords):
            if not args:
                raise TypeError("descriptor '__new__' of partial needs an argument")
            if len(args) < 2:
                raise TypeError("type 'partial' takes at least one argument")
            cls, func, *args = args
            if not callable(func):
                raise TypeError("the first argument must be callable")
            args = tuple(args)

            if hasattr(func, "func"):
                args = func.args + args
                tmpkw = func.keywords.copy()
                tmpkw.update(keywords)
                keywords = tmpkw
                del tmpkw
                func = func.func

            self = super(partial, cls).__new__(cls)

            self.func = func
            self.args = args
            self.keywords = keywords
            return self

        def __call__(*args, **keywords):
            if not args:
                raise TypeError("descriptor '__call__' of partial needs an argument")
            self, *args = args
            newkeywords = self.keywords.copy()
            newkeywords.update(keywords)
            return self.func(*self.args, *args, **newkeywords)

        @recursive_repr()
        def __repr__(self):
            qualname = type(self).__qualname__
            args = [repr(self.func)]
            args.extend(repr(x) for x in self.args)
            args.extend(f"{k}={v!r}" for (k, v) in self.keywords.items())
            if type(self).__module__ == "functools":
                return f"functools.{qualname}({', '.join(args)})"
            return f"{qualname}({', '.join(args)})"

        def __reduce__(self):
            return type(self), (self.func,), (self.func, self.args,
                   self.keywords or None, self.__dict__ or None)

        def __setstate__(self, state):
            if not isinstance(state, tuple):
                raise TypeError("argument to __setstate__ must be a tuple")
            if len(state) != 4:
                raise TypeError(f"expected 4 items in state, got {len(state)}")
            func, args, kwds, namespace = state
            if (not callable(func) or not isinstance(args, tuple) or
               (kwds is not None and not isinstance(kwds, dict)) or
               (namespace is not None and not isinstance(namespace, dict))):
                raise TypeError("invalid partial state")

            args = tuple(args) # just in case it's a subclass
            if kwds is None:
                kwds = {}
            elif type(kwds) is not dict: # XXX does it need to be *exactly* dict?
                kwds = dict(kwds)
            if namespace is None:
                namespace = {}

            self.__dict__ = namespace
            self.func = func
            self.args = args
            self.keywords = kwds

    def f(a, b, *, c):
        pass
    funcs = {
        'raw function': f,
        'C partial': functools.partial(f),
        'Py partial': partial(f),
        'dumb': autopartial(f),
        'signature': _autopartial2(f),
        'cached _sig': _autopartial3(f),
        'cached shortcut': _autopartial4(f)
        }
    for name, func in funcs.items():
        t = timeit.timeit(lambda: func(1, 2, c=3), number=100000)
        print('{:15}: {}'.format(name, t))

if __name__ == '__main__':
    benchmark()
