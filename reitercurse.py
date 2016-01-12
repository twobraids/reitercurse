#!/usr/bin/env python

from mock import MagicMock
from functools import wraps

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
            self.static_kwargs = tuple(
                kwargs_key_value for kwargs_key_value in kwargs.iteritems()
            )

    @property
    def kwargs(self):
        return dict(self.static_kwargs)

    def __iter__(self):
        yield self.args
        yield self.kwargs

    def __hash__(self):
        return (self.args, self.static_kwargs).__hash__()

    def __eq__(self, other):
        return self.args == other.args and self.static_kwargs == other.static_kwargs


class ExecutionStack(object):
    execution_stack = []
    in_use = False

    @classmethod
    def execute(kls):
        kls.in_use = True
        try:
            while kls.execution_stack:
                the_top_unknown = kls.execution_stack.pop()
                the_top_redemption_token = the_top_unknown.redemption_token

                try:
                    result_for_top_unknown = the_top_unknown.defining_function.result_cache[the_top_redemption_token]
                except KeyError:
                    next_args, next_kwargs = the_top_redemption_token
                    result_for_top_unknown = the_top_unknown.defining_function(*next_args, **next_kwargs)

                    if isinstance(result_for_top_unknown, UnknownValue):
                        # the result for the top unknown was another unknown
                        # push the top unknown back onto the stack
                        kls.execution_stack.append(the_top_unknown)
                        # the quest for a new value for the top unknown
                        # resulted in the creation of a new unknown. Fetch
                        # that new unknown from the unknown creation stack
                        # and push it onto the execution_stack
                        #result_for_top_unknown.defining_function.execution_stack.append(result_for_top_unknown)
                        kls.execution_stack.append(result_for_top_unknown)
                    else:
                        # constant case
                        the_top_unknown.defining_function.result_cache[the_top_redemption_token] = result_for_top_unknown
            return result_for_top_unknown
        finally:
            kls.in_use = False



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
    def create_unknown(*args, **kwargs):
        redemption_token=RedemptionToken(*args, **kwargs)
        class TaggedUnknownValue(UnknownValue):
            """Each set of recursive method arguments has its own
            TaggedUnknownValue type.  They contain a reference to the
            recursive function being wrapped by the decorator as well as
            a reference to the redemption token.
            """
            def __init__(self, *args, **kwargs):
                super(UnknownValue, self).__init__(
                    *args,
                    defining_function=fn,
                    redemption_token=redemption_token,
                    **kwargs
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
        try:
            if fn.result_cache:
                pass
        except AttributeError:
            fn.result_cache = {}
            fn.in_use = False

        local_redemption_token = RedemptionToken(*args, **kwargs)

        if local_redemption_token in fn.result_cache:
            # memoizing trap for calls to original function
            result = fn.result_cache[local_redemption_token]
            return result
        elif fn.in_use:
            # trap to capture any attempts to recurse beyond the 2 level of
            # the original function
            result = create_unknown(*args, **kwargs)
            return result
        # this section is reached iff it is the original client call to
        # the original function
        fn.in_use = True
        first_future = create_unknown(*args, **kwargs)
        if not ExecutionStack.in_use:
            ExecutionStack.execution_stack.append(first_future)
            result = ExecutionStack.execute()
        else:
            return first_future

        fn.in_use = False
        return result
    return wrapper

from collections import Sequence

@execute_iteratively
def isearch(t):
    my_evens = []
    if isinstance(t, Sequence):
        for item in t:
            evens = isearch(item)
            my_evens.extend(evens)
    elif isinstance(t, int):
        if not t % 2:
            my_evens.append(t)
    return my_evens


def rsearch(t):
    my_evens = []
    if isinstance(t, Sequence):
        for item in t:
            evens = rsearch(item)
            my_evens.extend(evens)
    elif isinstance(t, int):
        if not t % 2:
            my_evens.append(t)
    return my_evens

def grsearch(t):
    if isinstance(t, Sequence):
        for i in t:
            if isinstance(i, Sequence):
                for j in grsearch(i):
                    yield j
            else:
                if isinstance(i, int):
                    if not i % 2:
                        yield i




tree = (
    (
        (1, 3, 5),
        (2, 4, 5)
    ),
    (9, 11, 13),
    (22, 9),
    (
        (1, -33, 44),
        (
            (99, 100),
        )
    ),
    102,
    104,
    103
)

print [x for x in grsearch(tree)]

print isearch(tree)



def get_even(number):
    while True:
        if not number % 2:
            number = yield number
        number += 1




