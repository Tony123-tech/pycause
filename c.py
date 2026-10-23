from pycause import Caused

# 建立變數
x = Caused(10)
y = x - 5
z = y * 2

names = {id(x): "x", id(y): "y", id(z): "z"}

print("=== 1. Natural Language: Chinese Chain ===")
print(z.why(lang="zh", mode="chain", names=names))

print("\n=== 2. Natural Language: English Chain ===")
print(z.why(lang="en", mode="chain", names=names))

print("\n=== 3. Natural Language: Root Cause ===")
print(z.why(lang="zh", mode="root", names=names))

print("\n=== 4. Symbolic Differentiation ===")
f = x**2 + 3 * x + 1
df = f.differentiate(x)
print(f"f(x) = {f}")
print(f"f'(x) = {df}")

print("\n=== 5. Algebraic Simplification ===")
messy = (x * 1) + 0 - (x - x)
print(f"Before: {messy}")
print(f"After: {messy.simplify()}")

print("\n=== 6. Evaluation ===")
print(f"Value of f: {f.evaluate()}")
