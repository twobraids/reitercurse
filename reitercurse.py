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


def r2i(fn):
    """this decorator takes a recursive function and ensures that it gets
    evalutated iteratively instead.  To be successful, the recursive method
    must have the following attributes:
       1. parameters passed in must be hashable and static.
       2. return is used as the method of getting results, no side effects.

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
        future = UnknownValue()
        future.redemption_token = RedemptionToken(*args, **kwargs)
        fn.unknown_creation_stack.append(future)
        return future

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            if fn.recursion_monitoring_stack:
                pass
        except AttributeError:
            fn.recursion_monitoring_stack = []
            fn.execution_stack = []
            fn.result_cache = {}
            fn.unknown_creation_stack = []

        local_redemption_token = RedemptionToken(*args, **kwargs)
        fn.recursion_monitoring_stack.append(local_redemption_token)
        level = len(fn.recursion_monitoring_stack)
        assert local_redemption_token.args == args

        if local_redemption_token in fn.result_cache:
            # memoizing trap for calls to original function
            result = fn.result_cache[local_redemption_token]
        elif level > 1:
            # trap to capture any attempts to recurse beyond the 2 level of
            # the original function
            result = create_unknown(*args, **kwargs)
        else:
            # this section is reached iff it is the original client call to
            # the original function
            first_future = create_unknown(*args, **kwargs)
            fn.execution_stack.append(first_future)
            while fn.execution_stack:
                the_top_unknown = fn.execution_stack.pop()
                the_top_redemption_token = the_top_unknown.redemption_token

                try:
                    result_for_top_unknown = fn.result_cache[the_top_redemption_token]
                except KeyError:
                    next_args, next_kwargs = the_top_redemption_token
                    result_for_top_unknown = fn(*next_args, **next_kwargs)

                    if isinstance(result_for_top_unknown, UnknownValue):
                        # the result for the top unknown was another unknown
                        # push the top unknown back onto the stack
                        fn.execution_stack.append(the_top_unknown)
                        # the quest for a new value for the top unknown
                        # resulted in the creation of a new unknown. Fetch
                        # that new unknown from the unknown creation stack
                        # and push it onto the execution_stack
                        next_unknown = fn.unknown_creation_stack.pop()
                        fn.execution_stack.append(next_unknown)
                    else:
                        # constant case
                        fn.result_cache[the_top_redemption_token] = result_for_top_unknown
            result = result_for_top_unknown

        fn.recursion_monitoring_stack.pop()
        return result
    return wrapper




@r2i
def ifact(n):
    if n < 2:
        return 1
    else:
        return ifact(n - 1) * n

def rfact(n):
    if n < 2:
        return 1
    else:
        return rfact(n - 1) * n

assert (ifact(800) == rfact(800))

for x in range(10):
    print x, "ifact:", ifact(x), 'rfact:', rfact(x)
print 'ifact', 1001, ifact(1001), 'rfact:',
try:
    print rfact(1001)
except RuntimeError, e:
    print e



@r2i
def ifib(n):
    if n < 3:
        return n
    return ifib(n - 1) + ifib(n - 2)

def memo(fn):
    @wraps(fn)
    def wrapped(n):
        try:
            if n in fn.cache:
                return fn.cache[n]
        except AttributeError:
            fn.cache = {}
        result = fn(n)
        fn.cache[n] = result
        return result
    return wrapped

@memo
def rfib(n):
    if n < 3:
        return n
    return rfib(n - 1) + rfib(n - 2)

@r2i
def ifib1(n):
    if n < 3:
        return n
    return ifib1(n - 1) + ifib2(n - 2)

@r2i
def ifib2(n):
    if n < 3:
        return n
    return ifib2(n - 1) + ifib1(n - 2)


for x in range(10):
    print x, "ifib:", ifib(x), 'rfib:', rfib(x), 'ifib1', ifib1(x)
print 'ifib', 1001, ifib(1001), 'rfib:',
try:
    print rfib(1001)
except RuntimeError, e:
    print e


print 'ifib1(2000)', ifib1(10)


@r2i
def iisPalindrome(S):
    # Remove spaces in the string
    N = S.split()
    N = ''.join(N)
    if len(N) == 1 or len(N) == 0:
        return True
    else:
        if N[0] == N[-1] and iisPalindrome(N[1:-1]):
            return True
        else:
            return False


def risPalindrome(S):
    # Remove spaces in the string
    N = S.split()
    N = ''.join(N)
    if len(N) == 1 or len(N) == 0:
        return True
    else:
        if N[0] == N[-1] and risPalindrome(N[1:-1]):
            return True
        else:
            return False


assert (
    iisPalindrome('abba') == risPalindrome('abba')
)
assert (
    iisPalindrome('aoeu') == risPalindrome('aoeu')
)
assert (
    iisPalindrome('abba'*100) == risPalindrome('abba'*100)
)
assert (
    iisPalindrome('abeba') == risPalindrome('abeba')
)




@r2i
def ifib1(n):
    if n < 3:
        return n
    return ifib1(n - 1) + ifib2(n - 2)

@r2i
def ifib2(n):
    if n < 3:
        return n
    return ifib2(n - 1) + ifib1(n - 2)

