1. Assumption:

    a)  Base Case : T(n) <= a constant for all sufficiently small n

    b)  For all sufficiently large n : T(n) <= a T(n/b) + O(n^d) , where:

         i)  a = number of recursive calls on subproblems ( >= 1)

         ii)  b = input size shrinkage factor ( > 1)

         iii)  d = exponent in running time of "combine step" (>= 0)

         iv)  a, b, d are independent of n
         
2.  Master Method :

        if T(n) <= aT(n/b) + O(n^d)

 

                     O (n^d log n )     ,   a = b^d

        T(n) =       O (n^d)            ,   a < b^d

                     O (n^ (logb a) )   ,   a > b^d

3.  For recursion tree, at each level j=0, 1, 2, ..., logb n  , there are a^j subproblems each of size n/b^j.

     Total work at level j ( ignore work in recursive call ) <= a^j X c (n/b^j)^d = cn^d X (a/b^d)^j

      a = rate of subproblem proliferation ( RSP)

      b = rate of work shrinkage (RWS )

 

      i)  If RSP < RWS, then the amount of work is decreasing with the recursion level j.

           ==> most work at root

      ii)  If RSP > RWS, then the amount of work is increasing with the recursion level j.

           ==> most work at leaves

      iii)  If RSP and RWS are equal, then the amount of work is the same at every recursion level j.

           ==> same amount of work each level

 

      Total work <= cn^d X sum ( (a/b^d)^j ) (j=1~logb n)
      ![image](https://raw.githubusercontent.com/whw199833/2021_for_work/master/notes/Algorithm_Stanford_notes/picture_in_notes/1.jpg)
 
 4.  If a = b^d , then (a/b^d) ^j =1 , so the total work <= cn^d X (logb n +1 ) = O(n^d log n )

            ( logb n = logk n / logk b = 1/logk b X logk n , so b is not important for logb n , it can be any value , only a constant factor difference)

     let r = a/b^d , 1 + r + r^2 + r^3 + ... + r^k = r^(k+1) -1 / r - 1

    if r < 1 is constant , 1 + r + r^2 + ... + r^k <= 1/ (1-r)  = a constant (1st item of sum dominates)

     (i.e. 1/2 + 1/4 + 1/8 + ... <= 1/2 * 2 )

     so the total work <= cn^d X 1/(1-r) = O (n^d)

    if r > 1 is constant , 1 + r + r^2 + ... + r^k <= r^k ( 1+ 1/r-1)  ( last item of sum dominates)

     so the total work <= cn^d X logb n X r^logb n  = O ( a ^ logb n ) ( note : (1/b^d) ^logb n = 1/n^d) = O(n^logb a)

     actually a^logb n is the number of leaves of the recursion tree.
