import datetime
import json

from django.core import serializers
from django.shortcuts import render
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils import timezone
from librarian.models import Book, AllBook, BorrowOrder, ReserveOrder, Role
from reader.models import User
from administrator.models import Administrator
import time
import requests


def index(request):
    '''
    首页
    :param request:
    :return:
    '''

    username = request.session.get('username', "None")
    if username != "None":
        message = {'login': True, "username": username}
    else:
        message = {'login': False, "username": username}
    return render(request, 'index.html', message)


def manager_page(request):
    '''
    管理员界面
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == 'root':
        return render(request, 'manager_page.html')
    else:
        return HttpResponseRedirect(reverse("login"))


def clear_message(request):
    '''
    注销
    :param request:
    :return:
    '''
    del request.session["username"]
    return HttpResponseRedirect(reverse("index"))


def add_book(request):
    '''
    添加图书
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == 'root':
        return render(request, 'add_book.html')
    else:
        return HttpResponseRedirect(reverse("index"))


def add_reader(request):
    '''
    管理员添加读者
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == 'root':
        return render(request, 'add_reader.html')
    else:
        return HttpResponseRedirect(reverse("index"))


def delete_reader(request):
    '''
    管理员删除读者
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == 'root':
        if request.method == "GET":
            try:
                username = request.GET["username"]
                temp = User.objects.filter(user_name=username).delete()
                response = JsonResponse({'result': True})
                return response
            except Exception as e:
                return JsonResponse({'result': False})
    else:
        return HttpResponseRedirect(reverse("index"))


def update_reader_page(request):
    '''

    :param request:
    :return:
    '''

    username = request.session.get('username', "None")
    if username == 'root':
        username = ""
        email = ""
        try:
            username = request.GET["username"]
            email = request.GET["email"]
        except :
            pass
        return render(request, 'set_reader.html', {"username": username, "email": email})
    else:
        return HttpResponseRedirect(reverse("index"), )

def update_readerByMe(request):
    '''
    管理员修改读者
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == "None" :
        return HttpResponseRedirect(reverse("index"))
    if request.method == "GET":

        email = ""
        new_username = ""
        newPaw = ""
        try:
            try:
                oldPsw = request.GET["oldPsw"]
                newPaw = request.GET["newPaw"]
                confirPsw = request.GET["confirPsw"]
            except:
                pass
            temp = User.objects.get(user_name=username)
            if temp:
                if not email is "":
                    temp.email = email
                if not newPaw is "":
                    if oldPsw == temp.password:
                        temp.password = newPaw
                if not new_username is "":
                    temp.user_name = new_username
                temp.save()
                response = JsonResponse({'result': True})
            else:
                response = JsonResponse({'result': False})
            return response
        except Exception as e:
            return JsonResponse({'result': False})
    else:
        return HttpResponseRedirect(reverse("index"))



def update_reader(request):
    '''
    管理员修改读者
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == 'root':
        if request.method == "GET":
            username = ""
            email = ""
            new_username = ""
            password = ""
            try:
                try:
                    username = request.GET["username"]
                    email = request.GET["email"]
                    new_username = request.GET["new_username"]
                    password = request.GET["psw"]
                except:
                    pass
                temp = User.objects.get(user_name=username)
                if temp:
                    if not email is "":
                        temp.email = email
                    if not password is "":
                        temp.password = password
                    if not new_username is "":
                        temp.user_name = new_username
                    temp.save()
                    response = JsonResponse({'result': True})
                else:
                    response = JsonResponse({'result': False})
                return response
            except Exception as e:
                return JsonResponse({'result': False})
    else:
        return HttpResponseRedirect(reverse("index"))


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        else:
            return json.JSONEncoder.default(self, obj)


def get_reader_history(request):
    '''
    管理员查阅读者信息
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == 'root':
        if request.method == "GET":
                username = request.GET["username"]
                person = User.objects.filter(user_name=username).values()
                json_data = list(person)
                person_json_data = json.dumps(json_data, cls=DateEncoder, ensure_ascii=False)
                borHis = BorrowOrder.objects.filter(user=person[0]['user_id']).values()
                json_data = list(borHis)
                bor_json_data = json.dumps(json_data, cls=DateEncoder, ensure_ascii=False)
                resHis = ReserveOrder.objects.filter(user=person[0]['user_id']).values()
                json_data = list(resHis)
                resHis_json_data = json.dumps(json_data, cls=DateEncoder, ensure_ascii=False)

                response = JsonResponse({'person': person_json_data,'borHis': bor_json_data, 'resHis': resHis_json_data})
                return response
    else:
        return HttpResponseRedirect(reverse("index"))


def update_book_message_page(request):
    '''
    修改图书信息
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == 'root':
        if request.method == "GET":
            return render(request, 'set_book.html')
    else:
        return HttpResponseRedirect(reverse("index"))


def search_book_api(request):
    '''
    查询书籍API
    :param request:
    :return:
    '''
    is_administrator = False
    username = request.session.get('username', "None")
    if username == "None":
        return JsonResponse({"result": False, "msg": "未登录"})
    elif username == "root":
        is_administrator = True
    book_type = request.GET.get('book_type', None)
    book_name = request.GET.get('book_name', None)
    if book_name is None or book_type is None:
        return JsonResponse({"result": False, "msg": "查询参数不正确"})
    try:
        if book_type == "全部":
            result = Book.objects.filter(book_name__contains=book_name)
        else:
            result = Book.objects.filter(book_name__contains=book_name, type__contains=book_type)
        if len(result) > 0:
            result_json = render(request, 'result_json.html', {"book_list": result, "administrator": is_administrator})
            return JsonResponse({"result": True, "html": bytes.decode(result_json.content)})
        else:
            return JsonResponse({"result": False, "msg": "很抱歉未找到相关图书信息"})
    except :
        return JsonResponse({"result": False, "msg": "查询出错"})


def search_book(request):
    '''
    查询书籍
    :param request:
    :return:
    '''
    is_administrator = False
    username = request.session.get('username', "None")
    if username == "None":
        return JsonResponse({"result": False, "msg": "未登录"})
    elif username == "root":
        is_administrator = True
    book_type = request.GET.get('book_type', None)
    book_name = request.GET.get('book_name', None)
    if book_name is None or book_type is None:
        return JsonResponse({"result": False, "msg": "查询参数不正确"})
    try:
        if book_type == "全部":
            result = Book.objects.filter(book_name__contains=book_name)
        else:
            result = Book.objects.filter(book_name__contains=book_name, type__contains=book_type)
        return render(request, 'search_results.html', {"book_list": result, "administrator": is_administrator})

    except :
        return JsonResponse({"result": False, "msg": "查询出错"})


def reserve_api(request):
    '''
    预约API
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == "None":
        return JsonResponse({'result': False, "msg": "未登录"})
    if request.method == 'POST':
        isbn = request.POST['isbn']

        try:
            book = AllBook.objects.filter(isbn=isbn, is_available=True).first()
            user = User.objects.get(user_name=username)
            borrow = ReserveOrder.objects.filter(isbn=isbn, user_id=user.user_id, expire=False).first()
            if borrow:
                borrow.borrow_time = timezone.now()
                borrow.save()
                return JsonResponse({"result": True, "update": True})
            isbn = Book.objects.get(isbn=isbn)
        except Exception as e:
            return JsonResponse({'result': False, "msg": "数据库错误"})
        if not (book and user and isbn):
            return JsonResponse({'result': False, "msg": "未查到相关数据"})
        borrow_time = timezone.now()
        try:
            result = ReserveOrder.objects.create(book=book, user=user, borrow_time=borrow_time, successful=False,
                                                 isbn=isbn)
            if result:
                return JsonResponse({"result": True, "update": False})
            else:
                return JsonResponse({"result": False, "msg": "数据库保存失败"})
        except Exception as e:
            return JsonResponse({"result": False,  "msg": "数据库错误"})


def return_book_api(request):
    '''
    归还图书 API
    :param request:
    :return:
    '''
    if request.method != "POST":
        return JsonResponse({"result": False, "msg": "Forbidden"})
    username = request.session.get('username', "None")
    if not username == 'root':
        return JsonResponse({"result": False, "msg": "Forbidden"})
    try:
        borrow_id = request.POST["borrow_id"]
    except:
        return JsonResponse({"result": False, "msg": "Forbidden"})
    try:
        borrow_order = None
        try:
            borrow_order = BorrowOrder.objects.get(order_id=borrow_id)
        except:
            return JsonResponse({"result": False, "msg": "Borrow_order_id is invalid"})
        borrow_order.return_time = timezone.now()
        borrow_order.expire = True
        borrow_order.book.is_available = True
        if borrow_order.book.isbn.available_num < borrow_order.book.isbn.total_num:
            borrow_order.book.isbn.available_num = borrow_order.book.isbn.available_num + 1
        else:
            borrow_order.book.isbn.available_num = borrow_order.book.isbn.total_num
        borrow_order.book.isbn.save()
        borrow_order.save()
        return JsonResponse({"result": True})
    except Exception:
        return JsonResponse({"result": False, "msg": "Error!"})


def book_message_api(request):
    '''
    通过ISBN查询书籍
    :param request:
    :return: JSON数据
    '''
    isbn = request.GET.get('isbn', None)
    douban_url = 'https://api.douban.com/v2/book/isbn/'
    result_json ={}
    if isbn:
        result = requests.get(douban_url+isbn)
        if result.status_code == 200:
            result_json['result'] = True
            import json
            book_message = json.loads(result.text)
            if 'msg' not in book_message.keys():
                try:
                    result_json['price'] = book_message['price']
                    result_json['isbn'] = book_message['isbn13']
                    result_json['author'] = ','.join(book_message['author'])
                    result_json['image_url'] = book_message['image']
                    result_json['book_name'] = book_message['title']
                    result_json['type'] = ','.join([i['name'] for i in book_message['tags']])
                except KeyError:
                    pass
        else:
            result_json['result'] = False
        return JsonResponse(result_json)


def administrator_login_post(request):
    '''
    管理员登陆api
    :param request:
    :return:
    '''
    if request.method == "POST":
        try:
            user_type = request.POST["type"]
            if not user_type == 'administrator':
                return JsonResponse({'result': False})
            password = request.POST["password"]
            username = request.POST["username"]
            remember = request.POST['remember']
            temp = Administrator.objects.get(administrator_name=username, password=password)
            if temp:
                response = JsonResponse({'result': True})
                if not remember:
                    request.session.set_expiry(0)
                request.session["admin_name"] = temp.administrator_name
                request.session['username'] = 'root'
                request.session['login_time'] = time.time()
                request.session['type'] = 'administrator'
            else:
                response = JsonResponse({'result': False})
            return response
        except Exception as e:
            return JsonResponse({'result': False})


def borrow_book_api(request):
    '''
    预约图书API
    通过获取 reserve订单号,把预约订单变为借阅订单
    :param request:
    :return:
    '''
    if request.method != "POST":
        return JsonResponse({"result": False, "msg": "Forbidden"})
    username = request.session.get('username', "None")
    if not username == 'root':
        return JsonResponse({"result": False, "msg": "Forbidden"})
    try:
        reserve_id = request.POST["reserve_id"]
    except:
        return JsonResponse({"result": False, "msg": "Forbidden"})
    try:
        limit = Role.objects.all().first().books_limit
        reserve_order = None

        try:
            reserve_order = ReserveOrder.objects.get(order_id=reserve_id,)
        except:
            return JsonResponse({"result": False, "msg": "Reserve_id is invalid"})
        a = BorrowOrder.objects.filter(user_id=reserve_order.user.user_id, expire=False).count()
        if BorrowOrder.objects.filter(user_id=reserve_order.user.user_id, expire=False).count() >= limit:
            return JsonResponse({"result": False, "msg": "This User can not borrow!"})
        if reserve_order.isbn.available_num <= 0:
            return JsonResponse({"result": False, "msg": "All Book have been lent out!"})
        reserve_time = reserve_order.borrow_time
        delay = time.mktime(timezone.now().timetuple()) - time.mktime(reserve_time.timetuple())
        if delay > (60**2)*2:
            reserve_order.successful = False
            reserve_order.expire = True
            reserve_order.save()
            return JsonResponse({"result": True, "expire": True})
        borrow_time = timezone.now()
        book_id = reserve_order.book_id
        user_id = reserve_order.user_id
        BorrowOrder.objects.create(borrow_time=borrow_time,
                                   debt=0,
                                   is_return=False,
                                   book_id=book_id,
                                   user_id=user_id,
                                   expire=False)
        reserve_order.isbn.available_num = reserve_order.isbn.available_num - 1
        reserve_order.successful = True
        reserve_order.book.is_available = False
        reserve_order.expire = True
        reserve_order.isbn.save()
        reserve_order.save()
        return JsonResponse({"result": True, "expire": False})
    except Exception as e:
        print(e)
        return JsonResponse({"result": False, "msg": "Error!"})


def manage_user_api(request):
    '''
    管理界面请求用户信息
    :param request:
    :return:
    '''
    if request.method != "POST":
        return JsonResponse({"result": False, "msg": "Forbidden"})
    username = request.session.get('username', "None")
    if not username == 'root':
        return JsonResponse({"result": False, "msg": "Forbidden"})
    try:
        user_id = 0
        username = request.POST["user_name"]
        try:
            user = User.objects.get(user_name=username)
            if user:
                user_id = user.user_id
        except:
            return JsonResponse({"result": False, "msg": "User Name Invalid!"})
        reserve_order_list = ReserveOrder.objects.filter(user_id=user_id, expire=False, )
        borrow_order_list = BorrowOrder.objects.filter(user_id=user_id, expire=False)
        user_dict = {
            "user_name": user.user_name,
            "user_id": user.user_id,
            "email": user.email
        }
        reserve_orders = list()
        for reserve_order in reserve_order_list:
            order = {
                'reserve_order_id': reserve_order.order_id,
                "reserve_book_name": reserve_order.book.isbn.book_name,
                "reserve_user_name": user.user_name,
                "reserve_time": reserve_order.borrow_time
            }
            reserve_orders.append(order)
        borrow_orders = list()
        for borrow_order in borrow_order_list:
            order = {
                'borrow_order_id': borrow_order.order_id,
                "borrow_book_name": borrow_order.book.isbn.book_name,
                "borrow_user_name": user.user_name,
                "borrow_time": borrow_order.borrow_time,
                "debt": borrow_order.debt
            }
            borrow_orders.append(order)
        return JsonResponse(
                            {'result': True,
                             'user_message': user_dict,
                             'reserve_orders': reserve_orders,
                             'borrow_orders': borrow_orders
                             }
                            )
    except Exception:
        return JsonResponse({"result": False, "msg": "Error!"})


def add_book_api(request):
    '''
    添加图书
    :param request:
    :return:
    '''
    if request.method == "POST":
        try:
            isbn = request.POST['isbn']
            try:
                temp = Book.objects.get(isbn=isbn)
                if temp:
                    return JsonResponse({"result": False, 'msg': "该书已存在"})
            except Book.DoesNotExist:
                pass
            author = request.POST['author']
            book_name = request.POST['book_name']
            image_url = request.POST['image_url']
            total_num = request.POST['total_num']
            price = request.POST['price']
            type = request.POST["type"]
            place = request.POST['place']
            image_result = requests.get(image_url)
            if image_result.status_code == 200:
                with open("./librarian/static/book_image/%s.jpg" % isbn, "wb") as file:
                    file.write(image_result.content)
            image_url = '/static/book_image/%s.jpg' % isbn
            book = Book()
            book.isbn = isbn
            book.author = author
            book.book_name = book_name
            book.image_url = image_url
            book.total_num = total_num
            book.type = type
            book.place = place
            book.price = price
            book.available_num = total_num
            book.save()
            all_book_list = list()
            for x in range(int(total_num)):
                all_book_list.append(AllBook(isbn=book, is_available=True))
            AllBook.objects.bulk_create(all_book_list)
        except Exception as e:
            return JsonResponse({'result': False, "msg": "数据库保存错误"})
    return JsonResponse({'result': True})


def get_book(request):
    '''
    获取书的信息
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == 'root':
        if request.method == "GET":
            isbn = request.GET["isbn"]
            try:
                book = Book.objects.get(isbn=isbn)
            except:
                return JsonResponse({"result": False})
            response = JsonResponse({'result': True, 'isbn': isbn, "price": book.price,
                                     'author': book.author, 'book_name': book.book_name,
                                     'place': book.place, "total_num": book.total_num,
                                     'type': book.type
                                     })
            return response

    else:
        return HttpResponseRedirect(reverse("index"))


def update_book(request):
    '''
    管理员修改书的位置
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == 'root':
        if request.method == "GET":
                isbn = request.GET["isbn"]
                book = Book.objects.get(isbn=isbn)
                total_num = request.GET["total_num"]
                place = request.GET['place']
                type = request.GET['type']
                if book:
                    if not place is "":
                        book.place = place
                    if not type is "":
                        book.type = type
                    if not total_num is "":
                        add_num = int(total_num) - int(book.total_num)
                        if add_num >= 0:
                            try:
                                all_book_list = list()
                                for x in range(int(add_num)):
                                    all_book_list.append(AllBook(isbn=book, is_available=True))
                                AllBook.objects.bulk_create(all_book_list)
                                book.total_num = total_num
                            except:
                                pass
                        else:
                            response = JsonResponse({'result': False, "msg": "The quantity should not be less than the previous quantity."})
                            return response
                    book.save()
                    response = JsonResponse({'result': True})
                else:
                    response = JsonResponse({'result': False, "msg": "Unknown Error!"})
                return response
    else:
        return HttpResponseRedirect(reverse("index"))