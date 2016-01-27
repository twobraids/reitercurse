# reitercurse

This project is an intellectual exercise, not a serious project for production use. Maybe it will inspire someone to make a more serious version that accomplishes the same thing with more more aplomb and efficiency.  This implementation is likely full of problems, can't-get-there-from-here situations, or other such troubles.  There are no waranty, no guarantee, and the author is absentee.  

Herein is defined a decorator for use on a function written a recursive manner. Using deceit and misdirection, the decorator induces iterative behavior from the recursive function. The decorator hijacks the original method and traps all recursive calls, forcing them to return an Unknown object.  Each Unknown is pushed onto a stack for later evaluation.  When the stack is empty, the final value is returned.

simple case:

        @execute_iteratively
        def fact(n):
            if n < 2:
                return 1
            else:
                return fact(n - 1) * n
                

indirect recursion case:

        @execute_iteratively
        def ifib1(n):
            if n < 3:
                return n
            return ifib1(n - 1) + ifib2(n - 2)

        @execute_iteratively
        def ifib2(n):
            if n < 3:
                return n
            return ifib2(n - 1) + ifib1(n - 2)


muteable argument case:

        @execute_iteratively
        def i_quicksort(value_sequence):
            if not value_sequence:
                return []
            pivots = [x for x in value_sequence if x == value_sequence[0]]
            lesser = i_quicksort([x for x in value_sequence if x < value_sequence[0]])
            greater = i_quicksort([x for x in value_sequence if x > value_sequence[0]])
            return lesser + pivots + greater

              
