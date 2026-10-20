<!-- triage-replay: {"case_id": "c01", "original_created_at": "2025-10-06T19:26:28Z", "original_author_association": "NONE"} -->
Playground example below, but also reproduces with `async with` and `if` statements with compound boolean conditions (so perhaps related to upstream-issue-4731 but a priori does is not quite the same situation).

**Black https://github[.]com/psf/black/commit/314f8c**

[Playground link](https://black.vercel.app/?version=main&state=_Td6WFoAAATm1rRGAgAhARYAAAB0L-Wj4AC9AIBdAD2IimZxl1N_WmufDs0LpGEw9emYfCBl3bwWiaaPk-9VShmWdTZHtWIqHDNOo5vv3mtCRt2JPdYrP_88UxS71LUIZEYpZZ1dEE9hvybVY2-MCZ_Ou1Zl2ovnO0SjGtI8ifPSy2ScIBha4EzUEKo6liKlyiprVTWyJDh3AmX1byMAADAZ4agZ4L3QAAGcAb4BAADLeP5oscRn-wIAAAAABFla)

## Options

`--line-length=88`
`--safe`
`--preview`

## Input

```python
with open("file.txt") as f: content = f.read() # fmt: skip
```

## Output

```python
Cannot parse: 1:4: with
```

## Expected

```python
with open("file.txt") as f: content = f.read() # fmt: skip
```
