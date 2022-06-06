from pickle import TRUE


def test():
    try:
        return 1/0
    except ZeroDivisionError as e:
        raise ZeroDivisionError from e

def main():
    try:
        test()
    except Exception as e:
        if e == ZeroDivisionError:
            print(1)
        if type(e) == ZeroDivisionError:
            print(2)

main()
test_one = None
test_two = 'f'

if (test_two or test_one) == None:
    print(True)