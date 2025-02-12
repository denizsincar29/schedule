# CUtils- console utilities for user interaction

# exception: call failed
class CallFailed(Exception):
    def __init__(self, message):
        super().__init__(message)

# function: asks while callback raises an exception
def ask_while(callback, prompt):
    while True:
        try:
            result = input(prompt)
            return callback(result)
        except CallFailed as e:
            print(e)


# function: asks choice from list
# list can be any indexable object.
# enter n or b to go to the next or previous page if list is too long

def ask_choice_from_list(lst, prompt):
    # if list length is 0, return None
    if len(lst) == 0:
        return None
    if len(lst) == 1:
        return lst[0]
    print(prompt)
    page = 0
    pages = len(lst) // 10  # but if remainder > 0, we need one more page
    if len(lst) % 10 > 0:
        pages += 1
    while True:
        print(f"Страница {page + 1} из {pages}")
        for i, item in enumerate(lst[page * 10:page * 10 + 10]):
            print(f"{i + 1}. {item}")
        choice = input(" Введите номер варианта, n для следующей страницы, b для предыдущей: ")
        if choice.lower() in ["+", "n", "next", "д", "с", "след", "следующая", "далее", "дальше"]:
            page += 1
            if page >= pages:
                page = 0
        elif choice.lower() in ["-", "b", "back", "п", "н", "пред", "предыдущая", "назад"]:
            page -= 1
            if page < 0:
                page = pages - 1
        elif choice.lower() in ["q", "quit", "exit", "в", "выход"]:
            return None
        elif (choice.startswith("p") or choice.startswith("с")) and choice[1:].isdigit():
            try:
                page = int(choice[1:]) - 1
                if page < 0 or page >= pages:
                    print("Неверный номер страницы")
            except ValueError:
                print("Введите номер страницы")
        else:
            try:
                # get number of choices on the current page if it's the last page
                if page == pages - 1:
                    choices = len(lst) % 10
                else:
                    choices = 10
                choice = int(choice)
                if 1 <= choice <= choices:
                    return lst[page * 10 + choice - 1]
                else:
                    print("Неверный номер")
            except ValueError:
                print("Введите число")
    return None


if __name__ == "__main__":
    def test_callback(result):
        try:
            return int(result)
        except ValueError:
            raise CallFailed("Введи число")

    r = ask_while(test_callback, "Введите число: ")
    print(r)

    # now list! Make a list of all 26 english letters
    letters = [chr(i) for i in range(65, 91)]
    print(ask_choice_from_list(letters, "Выбери букву: "))
    # test with empty and 1-element list
    print(ask_choice_from_list([], "Выбери букву: "))
    print(ask_choice_from_list(["A"], "Выбери букву: "))