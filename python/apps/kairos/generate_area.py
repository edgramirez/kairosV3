global x1
global y1
global x2
global y2
global x3
global y3
global x4
global y4

def int_positive(value):
    try:
        value_int = int(value)
    except ValueError:
        print("Value should be integer")
        return False

    if value_int < 1:
        print("Value should be positive")
        return False

    return value_int

def set_x1():
    global x1
    while 1:
        x1 = input("Provide x1: ")
        x1 = int_positive(x1)
        if x1 is False:
            continue
        break

def set_y1():
    global y1
    while 1:
        y1 = input("Provide y1: ")
        y1 = int_positive(y1)
        if y1 is False:
            continue
        break

def set_x2():
    global x2,y1,y2
    while 1:
        x2 = input("Provide only x2, y2 will be equal to y1: ")
        x2 =  int_positive(x2)
        if x2 is False:
            continue
        y2 = y1
        break
    

def set_x3():
    global x3
    while 1:
        x3 = input("Provide x3: ")
        x3 = int_positive(x3)
        if x3 is False:
            continue
        if x3 < 2:
            print("x3:{} should be at least 2 or greater".format(x3))
            continue
        break

def set_y3():
    global y1,y3
    while 1:
        y3 = input("Provide y3: ")
        y3 = int_positive(y3)
        if y3 is False:
            continue
        if abs(y3-y1) < 2:
            print("y3 should be a value at least 2 greater or 2 lesser than y1")
            continue
        break
    
def set_x4():
    global x3,y3,x4,y4
    while 1:
        x4 = input("Provide only x4, y4 will be equal to y3: ")
        x4 = int_positive(x4)
        if x4 is False:
            continue
        if abs(x4-x3) < 2:
            print("x4 should be a value at least 2 greater or 2 lesser than x3")
            continue
        if x4>(x3-2):
            print("Wrong x4 coordinates, lines could not cross each other")
            continue
        y4 = y3
        break

#x's mayores que 2 para garantizar que existe un area en el cuadrilatero
#toda coordenada es diferente de (0,0)

def coordinates():
    set_x1()
    set_y1()
    print("({},{})".format(x1,y1))
    set_x2()
    print("({},{})".format(x2,y2))
    set_x3()
    set_y3()
    print("({},{})".format(x3,y3))
    set_x4()

    print("({},{})".format(x1,y1))
    print("({},{})".format(x2,y2))
    print("({},{})".format(x3,y3))
    print("({},{})".format(x4,y4))

coordinates()
