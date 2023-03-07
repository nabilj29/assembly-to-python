def fib(n):
    a = 0
    b = 1
    i = 0
    while i < n:
        tmp  = a + b
        a = b
        b = tmp
        i = i + 1
    return a

n = int(input())
result = fib(n)
print(result)