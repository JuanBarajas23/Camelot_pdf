array = [
    [6, 3],
    [14, 3],
    [2, 3]
]

first_sum = sum(item[0] for item in array)
second_value = array[0][1] if array else 0

shape = [first_sum, second_value]
print(shape)  # -> [22, 3]
