#!/usr/bin/env python

from mock import MagicMock
from functools import wraps

import threading

class UnknownValue(MagicMock):
    """instances of this class are used to represent a value that cannot be
    calculated at the current moment. It is a placeholder.  It is to be
    returned by calls to recursive functions to stop them from recursing.
    It is based on MagicMock because MagicMock is a class that can survive
    without error from statements like this:

        def recursive_method(x):
            # ...
            return recursive_method(x - 1) * 10 + recursive_method(x - 2) * 100

    The MagicMock captures the entire expression and returns an new instance
    of MagicMock.  Instance are placeholders only. No reconstruction of the
    expression is attempted from the MagicMock, it's just a thing that survives.
    """
    pass


class RedemptionToken(object):
    """this class serves as a token for redeeming a Future in the form of an
    UnknownValue.  It encapsulates a static form of args/kwargs from a call to
    a recursive function.  To redeem, the args/kwargs are passed to the
    recursive function and that function will either return a value or a new
    UnknownValue."""
    def __init__(self, *args, **kwargs):
            self.args = args

            args_list = []
            for x in args:
                if hasattr(x, '__hash__') and x.__hash__:
                    args_list.append(x)
                else:
                    # not necessarily the best way to freeze a
                    # mutable item - it assumes the mutable is a list
                    # of immutables
                    args_list.append(tuple(x))
            self.static_args = tuple(args_list)

            self.kwargs = kwargs
            kwargs_list = []
            for k, v in kwargs.iteritems():
                if hasattr(v, '__hash__') and v.__hash__:
                    kwargs_list.append((k, v))
                else:
                    # not necessarily the best way to freeze a
                    # mutable item - it assumes the mutable is a dict
                    # and that no state information is held within the
                    # values of the dict
                    kwargs_list.append ((k, tuple(v)))
            self.static_kwargs = tuple(kwargs_list)

    def __iter__(self):
        yield self.args
        yield self.kwargs

    def __hash__(self):
        try:
            return self.hash_value
        except AttributeError:
            self.hash_value = (self.static_args, self.static_kwargs).__hash__()
            return self.hash_value

    def __eq__(self, other):
        return self.static_args == other.static_args and self.static_kwargs == other.static_kwargs


class ExecutionStack(object):
    local_storage = threading.local()

    @classmethod
    def is_in_use(kls):
        try:
            return kls.local_storage.in_use
        except AttributeError:
            kls.local_storage.in_use = False
            return False

    @classmethod
    def get_execution_stack(kls):
        try:
            return kls.local_storage.execution_stack
        except AttributeError, x:
            kls.local_storage.execution_stack = []
            return kls.local_storage.execution_stack

    @classmethod
    def execute(kls):
        kls.local_storage.in_use = True
        try:
            execution_stack = kls.get_execution_stack()
            while execution_stack:
                the_top_unknown = execution_stack.pop()
                the_top_redemption_token = the_top_unknown.redemption_token

                try:
                    result_for_top_unknown = the_top_unknown.defining_function.local_storage.result_cache[the_top_redemption_token]
                except KeyError:
                    next_args, next_kwargs = the_top_redemption_token
                    result_for_top_unknown = the_top_unknown.defining_function(*next_args, **next_kwargs)

                    if isinstance(result_for_top_unknown, UnknownValue):
                        # the result for the top unknown was another unknown
                        # push the top unknown back onto the stack
                        execution_stack.append(the_top_unknown)
                        # the quest for a new value for the top unknown
                        # resulted in the creation of a new unknown. Fetch
                        # that new unknown from the unknown creation stack
                        # and push it onto the execution_stack
                        #result_for_top_unknown.defining_function.execution_stack.append(result_for_top_unknown)
                        execution_stack.append(result_for_top_unknown)
##                        print "PUSH", execution_stack
                    else:
                        # constant case
                        the_top_unknown.defining_function.local_storage.result_cache[the_top_redemption_token] = result_for_top_unknown
##                        print "POP ", execution_stack
            return result_for_top_unknown
        finally:
            kls.local_storage.in_use = False
            kls.local_storage.execution_stack = []



def execute_iteratively(fn):
    """this decorator takes a recursive function and ensures that it gets
    evalutated iteratively instead.  To be successful, the recursive method
    must have the following attributes:
       1. parameters passed in must be hashable and static.
       2. return is used as the method of getting results, no side effects.
       3. the value returned must be 'mockable'.

    The decorator accomplishes the task by trapping each call to the recurisive
    method.  There are three outcomes:
       1. the original call initiated by the client. In a while loop, call the
          recursive function, pushing each result onto a stack. Continue until
          the stack becomes empty and the only thing left is a value
       2. the decorator memoizes results keyed by the args/kwargs of the method
          call.  If there is a cache hit, return the cached value rather than
          calling the recursive function.
       3. this decorator actually allows recursion down to the second level.
          The original client call is the first level.  The iterative steps in
          #1 above will make the second level calls to try to get the recursive
          function to return real values.  If the recursive method tries to
          recurse beyond this level, the call is trapped and forced to return
          an "Unknown" with a redemption key that is the args/kwargs that was
          attempted in the recursive call.
    """
    def create_unknown(*outer_args, **outer_kwargs):
        redemption_token=RedemptionToken(*outer_args, **outer_kwargs)
        class TaggedUnknownValue(UnknownValue):
            """Each set of recursive method arguments has its own
            TaggedUnknownValue type.  They contain a reference to the
            recursive function being wrapped by the decorator as well as
            a reference to the redemption token.

            by defining this within the scope of this method, the underlying
            MagicMock will know about both 'fn' and the 'redemption_token'.
            That means that any children of that MagicMock will also have
            those values. This enables statements like:
                return fn(n - 1) * n
            to return a child mock that still has the context of the original
            call.
            """
            def __init__(self, *args, **kwargs):
                super(UnknownValue, self).__init__(
                    defining_function=fn,
                    redemption_token=redemption_token,
                )

            def __repr__(self):
                return str((
                    self.defining_function.func_name,
                    self.redemption_token.args,
                    self.redemption_token.kwargs
                ))
        future = TaggedUnknownValue()
        return future

    @wraps(fn)
    def wrapper(*args, **kwargs):
        """This is the method that actually replaces the recursive function
        and traps the calls to that function. """

        local_redemption_token = RedemptionToken(*args, **kwargs)

        try:
            if local_redemption_token in fn.local_storage.result_cache:
                # memoizing trap for calls to original function
                result = fn.local_storage.result_cache[local_redemption_token]
                return result
        except AttributeError:
            fn.local_storage = threading.local()
            fn.local_storage.result_cache = {}
            fn.local_storage.in_use = False

        if fn.local_storage.in_use:
            # trap to capture any attempts to recurse beyond the 2 level of
            # the original function
            result = create_unknown(*args, **kwargs)
            return result
        # this section is reached iff it is the original client call to
        # the original function
        fn.local_storage.in_use = True
        first_future = create_unknown(*args, **kwargs)
        if not ExecutionStack.is_in_use():
            ExecutionStack.get_execution_stack().append(first_future)
##            print "PUSH", ExecutionStack.get_execution_stack()
            try:
                result = ExecutionStack.execute()
            except BaseException:
                # we've no idea what kind of exceptions could be raised
                # by the function fn, so we've got to catch them all
                # and make sure that the flag about fn in use has to get
                # reset
                fn.local_storage.in_use = False
                raise
        else:
            return first_future

        fn.local_storage.in_use = False
        return result
    return wrapper

