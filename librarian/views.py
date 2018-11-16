import datetime
import json
import threading

from tool.bar_code import BarCode
from django.shortcuts import render
from django.http import HttpResponseRedirect, JsonResponse, FileResponse
from django.urls import reverse
from django.utils import timezone
from librarian.models import Book, AllBook, BorrowOrder, ReserveOrder, Role, Notice, AutoUpdateDB, BookDelHistory, \
    MoneyOrder, BookType, BookLocation
from reader.models import User
from administrator.models import Administrator
import time
import requests

from tool.changePsw import SendEmail
from tool.change_time import time_stamp_to_str


def index(request):
    '''
    首页
    :param request:
    :return:
    '''
    try:
        AutoUpdateDB.objects.get(updated_date=datetime.date.today())
    except:
        flag = True  # 邮件发送失败将变为false
        # 每天第一次访问主页将自动更新每本书的罚金
        all_borrow_orders = BorrowOrder.objects.all()
        role = Role.objects.first()
        for each in all_borrow_orders:
            if not each.is_return:  # 如果图书没有归还
                # 如果逾期
                if timezone.now() - each.borrow_time > timezone.timedelta(days=role.days_limit):
                    expire_days = (timezone.now() - each.borrow_time -
                                   timezone.timedelta(days=role.days_limit)).days
                    each.debt = role.fine * (expire_days + 1)  # 罚金
                    if not each.expire:  # 如果没设置到期
                        each.expire = True

                    # 向没有发过提醒邮件的用户发送邮件
                    if not each.is_alert:  # 如果没有发过提醒邮件
                        expire_date = time_stamp_to_str((each.borrow_time + timezone.timedelta(days=role.days_limit)).timetuple())
                        content = '您所借图书《' + each.book.the_book.book_name + '》已于 ' + str(expire_date) +\
                                  ' 到期，现罚金为 ' + str(each.debt) + ' 元，请及时归还图书并缴纳罚金，谢谢！'
                        s = SendEmail()
                        if s:  # 如果登录成功
                            is_successful = s.send("Bibliosoft 图书到期提醒", content, each.user.email)
                            s.close_smtp()
                            if not is_successful:
                                flag = False
                                print('Send alert email to user ' + each.user.user_name + ' about book 《' +
                                      each.book.the_book.book_name + '》: Failure!')
                            else:
                                print('Send alert email to user ' + each.user.user_name + ' about book 《' +
                                      each.book.the_book.book_name + '》: Success!')
                                each.is_alert = True

                    each.save()  # 数据库保存

        if flag:
            AutoUpdateDB.objects.create(is_updated=True)

    username = request.session.get('username', "None")
    # 获取最近5条通知
    notices = Notice.objects.filter().order_by('-updated_time')
    for i in range(len(notices)):  # 去掉回车换行，换成空格
        notices[i].content = notices[i].content.replace("\n", " ")
        notices[i].content = notices[i].content.replace("\r", " ")
    if username != "None":
        if username == 'anti_man':  # 如果是系统管理员，不能在主页登录
            message = {'login': False, "username": None, 'notices': notices}
        else:
            message = {'login': True, "username": username, 'notices': notices}
    else:
        message = {'login': False, "username": username, 'notices': notices}
    return render(request, 'index.html', message, )


def book_detail(request):
    '''
    图书详情
    :param request:
    :return:
    '''
    is_administrator = False
    username = request.session.get('username', "None")
    if username == "None":
        return HttpResponseRedirect(reverse("login"))
    elif username == "root":
        is_administrator = True
    try:
        book_id = request.GET['book_id']
        book = Book.objects.get(id=book_id)
        all_book = AllBook.objects.filter(the_book=book)
        return render(request, 'book_detail.html', {"books": all_book, "administrator": is_administrator, "bookname":book.book_name})
    except Exception as e:
        return JsonResponse({'error': e})


def manager_page(request):
    '''
    管理员界面
    :param request:
    :return:
    '''
    reserve_orders = ReserveOrder.objects.filter(expire=False)
    if len(reserve_orders) > 0:
        for reserve in reserve_orders:
            reserve_time = reserve.borrow_time
            delay = time.time() - time.mktime(reserve_time.timetuple())
            if delay > (60 ** 2) * 2:
                reserve.successful = False
                reserve.expire = True
                reserve.book.status = 0
                reserve.book.is_available = True
                reserve.the_book.available_num += 1
                reserve.the_book.save()
                reserve.book.save()
                reserve.save()

    username = request.session.get('username', "None")
    if username == 'root':
        librarian_name = request.session['admin_name']
        return render(request, 'manager_page.html', {'librarian_name': librarian_name})
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


def directly_borrow_book_api(request):
    '''
    管理员直接借书
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username != "root":
        return JsonResponse({"result": False, "error": "forbidden!"})
    try:
        if request.method == 'POST':
            book_id = request.POST['book_id']
            user_name_k = request.POST["user_name"]
            user = User.objects.get(user_name=user_name_k)
            user_id = user.user_id
            book = AllBook.objects.get(book_id=book_id)
            reserve_num = ReserveOrder.objects.filter(user=user_id, expire=False).count()
            limit = Role.objects.all().first().books_limit - reserve_num
            if book.status == 2:
                return JsonResponse({"result": False, "msg": "This book has been lent out!"})
            if book.status == 3:
                return JsonResponse({"result": False, "msg": "This book has been deleted!"})
            if user.borrow_num >= limit:
                return JsonResponse({"result": False, "msg": "This User can not borrow!"})

            borrow_time = timezone.now()

            BorrowOrder.objects.create(borrow_time=borrow_time,
                                       debt=0,
                                       is_return=False,
                                       book_id=book_id,
                                       user_id=user_id,
                                       expire=False)
            book.the_book.available_num = book.the_book.available_num - 1
            #  book.is_available = False
            book.status = 2
            user.borrow_num += 1
            book.save()
            user.save()
            book.the_book.save()
            return JsonResponse({"result": True, "expire": False})
    except Exception as e:
        return JsonResponse({"result": False, "msg": "Error!"})


def book_detail_api(request):
    '''
    单本的信息
    :param request:
    :return:
    '''
    book_id = 0
    username = request.session.get('username', "None")
    if username == "None":
        return JsonResponse({"error": "forbidden!"})
    if request.method == 'POST':
        book_id = request.POST['book_id']
    try:
        book = AllBook.objects.get(book_id=book_id)
        if book:
            return JsonResponse({"result": True, "book_id": book.book_id, "book_name": book.the_book.book_name,
                                 "book_status": book.status, "book_place": book.the_book.place})
    except Exception as e:
        return JsonResponse({"result": False, "msg": "can not find this book"})


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
                librarian_name = request.session["admin_name"]
                user = User.objects.get(user_name=username)
                librarian = Administrator.objects.get(administrator_name=librarian_name)
                borrow_order_list = BorrowOrder.objects.filter(user=user)
                for borrow_order in borrow_order_list:
                    if not borrow_order.is_return:
                        return JsonResponse({'result': False, 'msg': 'Please return all the books!'})
                    if borrow_order.debt != 0:
                        return JsonResponse({'result': False, 'msg': 'Please pay the debt!'})

                deposit_order = MoneyOrder.objects.get(order_type='D', user=user)

                money_order = MoneyOrder()
                money_order.user = user
                money_order.order_type = 'D'
                money_order.num = 0 - deposit_order.num
                money_order.librarian = librarian
                money_order.save()

                user.is_deleted = True
                response = JsonResponse({'result': True})
                return response
            except Exception as e:
                print(e)
                return JsonResponse({'result': False})
    else:
        return HttpResponseRedirect(reverse("index"))


# 图书管理员缴纳罚金
def manager_pay_debt_api(request):
    username = request.session.get('username', "None")
    if username == 'root':
        if request.method == "GET":
            try:
                username = request.GET["username"]
                librarian_name = request.session["admin_name"]
                librarian = Administrator.objects.get(administrator_name=librarian_name)
                user = User.objects.get(user_name=username)
                debt_orders = BorrowOrder.objects.filter(user=user, is_return=True)

                # 将罚金置为0
                all_fine = 0
                for debt_order in debt_orders:
                    if debt_order.debt > 0:
                        all_fine += debt_order.debt
                        debt_order.debt = 0
                        debt_order.save()

                # 如果没有欠费
                if all_fine == 0:
                    return JsonResponse({'result': False, 'msg': 'No Debt!'})
                else:
                    # 添加交易记录
                    MoneyOrder.objects.create(user=user, order_type='F',
                                              num=all_fine, librarian=librarian)

                    return JsonResponse({'result': True})
            except Exception as e:
                return JsonResponse({'result': False, 'msg': "Error!"})
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


def download_book_bar_code_api(request, bar_num):
    '''
    下载条形码
    :param request
    :param bar_num:
    :return:
    '''
    try:
        result = BarCode.create_bar_code(bar_num)
        if not result[0]:
            return JsonResponse(request, {'result': False})
        file = open(result[3], 'rb')
        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="%d.png"' % int(bar_num)
        return response
    except Exception as e:
        return JsonResponse({'result': False, 'msg': str(e)})


def update_readerByMe(request):
    '''
    管理员修改读者
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == "None":
        return HttpResponseRedirect(reverse("login"))
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
                    else:
                        return JsonResponse({'result': False})
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


def update_readerByMeInfo(request):
    '''
    更新读者信息
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == "None" :
        return HttpResponseRedirect(reverse("login"))
    if request.method == "GET":

        email = ""
        new_username = ""
        try:
            try:
                email = request.GET["email"]
                new_username = request.GET["user_name"]
            except:
                pass
            temp = User.objects.get(user_name=username)
            if temp:
                if not email is "":
                    temp.email = email
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
                response = JsonResponse({'person': person_json_data, 'borHis': bor_json_data, 'resHis': resHis_json_data})
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


def edit_type_location_page(request):
    '''
    编辑图书类别及位置
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == 'root':
        if request.method == "GET":
            all_book_type = BookType.objects.filter(is_deleted=False)
            all_book_location = BookLocation.objects.filter(is_deleted=False)
            return render(request, 'edit_info.html', {'all_book_type': all_book_type,
                                                      'all_book_location': all_book_location})
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
        return HttpResponseRedirect(reverse("login"))
        # return JsonResponse({"result": False, "msg": "Not logged in!"})
    elif username == "root":
        is_administrator = True
    book_type = request.GET.get('book_type', None)
    book_name = request.GET.get('book_name', None)
    if book_name is None or book_type is None:
        return JsonResponse({"result": False, "msg": "查询参数不正确"})
    try:
        if book_type == "ALL":
            result = Book.objects.filter(book_name__contains=book_name)
        else:
            if book_name == "":
                result = Book.objects.filter(type=book_type)
            else:
                result = Book.objects.filter(book_name__contains=book_name, type=book_type)
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
        return HttpResponseRedirect(reverse("login"))
    elif username == "root":
        is_administrator = True
    elif username == "anti_man":
        return HttpResponseRedirect(reverse("login"))
    book_type = request.GET.get('book_type', None)
    book_name = request.GET.get('book_name', None)

    if book_name is None or book_type is None:
        return JsonResponse({"result": False, "msg": "Query parameter incorrect!"})  # 查询参数不正确
    try:
        if book_type == "ALL":
            result = Book.objects.filter(book_name__contains=book_name) | Book.objects.filter(author__contains=book_name)
        else:
            if book_name == "":
                result = Book.objects.filter(type=book_type)
            else:
                result = Book.objects.filter(book_name__contains=book_name, type=book_type)\
                         | Book.objects.filter(author__contains=book_name, type=book_type)

        return render(request, 'search_results.html', {"book_list": result, "administrator": is_administrator,
                                     "username": username, 'search_text': book_name, 'search_type': book_type})

    except :
        return JsonResponse({"result": False, "msg": "Query error!"})  # 查询出错


def delete_book(request):
    '''
    删除书籍
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == 'root':
        return render(request, 'del_book.html')
    else:
        return HttpResponseRedirect(reverse("index"))


def del_record(request):
    '''
    删除书籍记录
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == 'root':
        all_del_history = BookDelHistory.objects.all().order_by('-deleted_time')
        return render(request, 'del_message.html', {'all_del_history': all_del_history})
    else:
        return HttpResponseRedirect(reverse("index"))


def delete_book_api(request):
    '''
    删除书
    :param request:
    :return:
    '''
    if request.method == "GET":
        book_id = request.GET.get("book_id", None)
        delreason = request.GET.get("del_reason", None)
        libraian_name = request.session["admin_name"]
        libraian = Administrator.objects.get(administrator_name=libraian_name)

        if delreason == 'damaged':
            del_reason = 'D'
        elif delreason == 'lost':
            del_reason = 'L'
        else:
            del_reason = None

        if book_id is None:
            return JsonResponse({"result": False, "msg": "Book ID can not be empty!"})  # Book ID 不能为空！
        else:
            try:
                del_book = AllBook.objects.get(book_id=book_id)
                book = Book.objects.get(id=del_book.the_book.id)
                if del_book.status == 2:  # 如果书已借出
                    borrow_order = BorrowOrder.objects.get(book=del_book)
                    user = User.objects.get(user_id=borrow_order.user.user_id)
                    MoneyOrder.objects.create(user=user, order_type='F', num=book.price, librarian=libraian)
                    borrow_order.debt = 0
                    borrow_order.return_time = timezone.now()
                    borrow_order.is_return = True
                    borrow_order.book.is_available = True
                    borrow_order.user.borrow_num -= 1

                    borrow_order.book.save()
                    borrow_order.user.save()
                    borrow_order.save()

                # 添加删除记录
                delhistory = BookDelHistory()
                delhistory.book_id = book_id
                delhistory.book_name = book.book_name
                if not (book.isbn is None):
                    delhistory.book_isbn = book.isbn
                delhistory.book_author = book.author
                delhistory.librarian = libraian
                delhistory.del_reason = del_reason

                book.total_num -= 1  # 此图书总数减1
                book.available_num -= 1
                book.save()

                # 删除这本图书
                del_book.status = 3
                del_book.is_available = False
                del_book.save()
                delhistory.save()
                return JsonResponse({"result": True})

            except Exception as e:
                print(e)
                return JsonResponse({"result": False, "msg": "Please input correct ID!"})  # 请输入正确id
    else:
        return HttpResponseRedirect(reverse("index"))


def post_news_record(request):
    '''
    推送消息记录
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == 'root':
        all_notices = Notice.objects.all().order_by("-updated_time")
        for i in range(len(all_notices)):  # 去掉回车换行，换成空格
            all_notices[i].content = all_notices[i].content.replace("\n", " ")
            all_notices[i].content = all_notices[i].content.replace("\r", " ")
        return render(request, 'post_news_record.html', {'all_notices': all_notices})
    else:
        return HttpResponseRedirect(reverse("index"))


def post_news(request):
    '''
    推送消息
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == 'root':
        librarian_name = request.session["admin_name"]
        librarian = Administrator.objects.get(administrator_name=librarian_name)

        return render(request, 'post_news.html', {'librarian': librarian})
    else:
        return HttpResponseRedirect(reverse("index"))


def income_record(request):
    username = request.session.get('username', "None")
    if username == 'root':
        all_money_orders = MoneyOrder.objects.all().order_by('-order_time')
        all_money = 0
        all_fine = 0
        all_deposit = 0
        for order in all_money_orders:
            all_money += order.num
            if order.order_type == 'D':
                all_deposit += order.num
            else:
                all_fine += order.num

        all_money = '%.2f' % all_money
        all_deposit = '%.2f' % all_deposit
        all_fine = '%.2f' % all_fine
        return render(request, 'income_record.html',
                      {'all_money_orders': all_money_orders, 'all_money': all_money,
                       'all_fine': all_fine, 'all_deposit': all_deposit})
    else:
        return HttpResponseRedirect(reverse("index"))


def reserve_api(request):
    '''
    预约API
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == "None":
        return JsonResponse({"error": "forbidden!"})
    if request.method == 'POST':
        book_id = request.POST['book_id']

        try:
            role = Role.objects.first()
            book = AllBook.objects.get(book_id=book_id)
            user = User.objects.get(user_name=username)
            if not (book and user):
                return JsonResponse({'result': False, "msg": "No relevant data was found!"})  # 未查到相关数据
            reserve_orders = ReserveOrder.objects.filter(user_id=user.user_id, expire=False)
            for reserve in reserve_orders:
                reserve_time = reserve.borrow_time
                delay = time.mktime(timezone.now().timetuple()) - time.mktime(reserve_time.timetuple())
                if delay > (60 ** 2) * 2:
                    reserve.successful = False
                    reserve.expire = True
                    reserve.book.status = 0
                    reserve.book.is_available = True
                    reserve.the_book.available_num += 1
                    reserve.the_book.save()
                    reserve.book.save()
                    reserve.save()
                    reserve_orders.delete(reserve)
            if len(reserve_orders) >= role.books_limit-user.borrow_num:
                return JsonResponse({"result": False, "msg": "You can not reserve it!"})
            borrow_time = timezone.now()
            result = ReserveOrder.objects.create(book=book, user=user, borrow_time=borrow_time, successful=False,
                                                 the_book=book.the_book)
            if result:
                book.status = 1
                book.is_available = False
                book.save()
                the_book = Book.objects.get(id=book.the_book_id)
                the_book.available_num -= 1
                the_book.save()
                return JsonResponse({"result": True, "update": False})
            else:
                return JsonResponse({"result": False, "msg": "Database save failed"})  # 数据库保存失败
        except Exception as e:
            return JsonResponse({'result': False, "msg": e})  # 数据库错误


        # except Exception as e:
        #     return JsonResponse({"result": False,  "msg": "Database Error!"})


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
        borrow_order.is_return = True
        borrow_order.book.is_available = True
        borrow_order.user.borrow_num -= 1
        if borrow_order.book.the_book.available_num < borrow_order.book.the_book.total_num:
            borrow_order.book.the_book.available_num = borrow_order.book.the_book.available_num + 1
        else:
            borrow_order.book.the_book.available_num = borrow_order.book.the_book.total_num
        borrow_order.user.save()
        borrow_order.book.status = 0
        borrow_order.book.the_book.save()
        borrow_order.book.save()
        borrow_order.save()
        return JsonResponse({"result": True})
    except Exception as e:
        print(e)
        return JsonResponse({"result": False, "msg": "Error!"})


def send_mail_api(request):
    if request.method != "POST":
        return JsonResponse({"result": False, "msg": "Forbidden"})
    # username = request.session.get('username', "None")
    # if not username == 'root':
    #     return JsonResponse({"result": False, "msg": "Forbidden"})
    try:
        borrow_id = request.POST["borrow_id"]
    except:
        return JsonResponse({"result": False, "msg": "Forbidden"})

    try:
        borrow_order = BorrowOrder.objects.get(order_id=borrow_id)
        role = Role.objects.first()
    except:
        return JsonResponse({"result": False, "msg": "Borrow_order_id is invalid"})

    try:
        if borrow_order.debt <= 0:  # 图书未到期
            return JsonResponse({"result": False, "msg": "This borrower_order is't expire"})
        else:
            expire_date = time_stamp_to_str((borrow_order.borrow_time + timezone.timedelta(days=role.days_limit)).timetuple())
            content = '您所借图书《' + borrow_order.book.the_book.book_name + '》已于 ' + expire_date + \
                      ' 到期，现罚金为 ' + str(borrow_order.debt) + ' 元，请及时归还图书并缴纳罚金，谢谢！'
            s = SendEmail()
            if s:  # 如果登录成功
                is_successful = s.send("图书到期提醒", content, borrow_order.user.email)
                s.close_smtp()
                if is_successful:
                    return JsonResponse({"result": True, "msg": "Send email successful!"})
                else:
                    return JsonResponse({"result": False, "msg": "Send email failure!"})
            else:
                return JsonResponse({"result": False, "msg": "Sign in the email failure!"})
    except Exception as e:
        print(e)
        return JsonResponse({"result": False, "msg": "Send email failure!"})

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
            temp = Administrator.objects.get(administrator_name=username, password=password, is_available=True)
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
            reserve_order = ReserveOrder.objects.get(order_id=reserve_id)
            if reserve_order.book.status == 2:
                return JsonResponse({"result": False, "msg": "This book has been lent out!"})
            if reserve_order.book.status == 3:
                return JsonResponse({"result": False, "msg": "This book has been deleted!"})

        except:
            return JsonResponse({"result": False, "msg": "Reserve_id is invalid"})

        if BorrowOrder.objects.filter(user_id=reserve_order.user.user_id, is_return=False).count() >= limit:
            return JsonResponse({"result": False, "msg": "This User can not borrow!"})
        if reserve_order.the_book.available_num <= 0:
            return JsonResponse({"result": False, "msg": "All Book have been lent out!"})
        reserve_time = reserve_order.borrow_time
        delay = time.mktime(timezone.now().timetuple()) - time.mktime(reserve_time.timetuple())
        if delay > (60 ** 2) * 2:
            reserve_order.successful = False
            reserve_order.expire = True
            reserve_order.book.status = 0
            reserve_order.book.is_available = True
            reserve_order.the_book.available_num += 1
            reserve_order.the_book.save()
            reserve_order.book.save()
            reserve_order.save()
            return JsonResponse({"result": True, "expire": True})

        borrow_time = timezone.now()
        book_id = reserve_order.book.book_id
        user_id = reserve_order.user.user_id

        BorrowOrder.objects.create(borrow_time=borrow_time,
                                   debt=0,
                                   is_return=False,
                                   book_id=book_id,
                                   user_id=user_id,
                                   expire=False)

        #  reserve_order.the_book.available_num = reserve_order.the_book.available_num - 1
        reserve_order.successful = True

        reserve_order.book.is_available = False
        reserve_order.book.status = 2
        reserve_order.expire = True
        reserve_order.user.borrow_num += 1

        reserve_order.book.save()
        reserve_order.user.save()
        reserve_order.the_book.save()
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
            user = User.objects.get(user_name=username, is_deleted=False)
            if user:
                user_id = user.user_id
        except:
            try:
                user = User.objects.get(user_id=username, is_deleted=False)
                if user:
                    user_id = user.user_id
            except:
                return JsonResponse({"result": False, "msg": "User Name Invalid!"})
        reserve_order_list = ReserveOrder.objects.filter(user_id=user_id, expire=False,).order_by('-borrow_time')
        borrow_order_list = BorrowOrder.objects.filter(user_id=user_id, is_return=False).order_by('-borrow_time')
        returned_order_list = BorrowOrder.objects.filter(user_id=user_id, is_return=True).order_by('-return_time')
        money_order_list = MoneyOrder.objects.filter(user=user).order_by('-order_time')

        user_dict = {
            "user_name": user.user_name,
            "user_id": user.user_id,
            "email": user.email
        }

        reserve_orders = list()
        for reserve_order in reserve_order_list:
            reserve_time = reserve_order.borrow_time
            delay = time.mktime(timezone.now().timetuple()) - time.mktime(reserve_time.timetuple())
            if delay > (60 ** 2) * 2:
                reserve_order.successful = False
                reserve_order.expire = True
                reserve_order.book.status = 0
                reserve_order.book.is_available = True
                reserve_order.the_book.available_num += 1
                reserve_order.the_book.save()
                reserve_order.book.save()
                reserve_order.save()
                continue
            order = {
                'reserve_order_id': reserve_order.order_id,
                "reserve_book_name": reserve_order.the_book.book_name,
                "reserve_book_id": reserve_order.book.book_id,
                "reserve_time": time_stamp_to_str(reserve_order.borrow_time.timetuple())
            }
            reserve_orders.append(order)

        borrow_orders = list()
        for borrow_order in borrow_order_list:
            order = {
                'borrow_order_id': borrow_order.order_id,
                "borrow_book_name": borrow_order.book.the_book.book_name,
                "borrow_book_id": borrow_order.book.book_id,
                "borrow_time": time_stamp_to_str(borrow_order.borrow_time.timetuple()),
                "debt": borrow_order.debt
            }
            borrow_orders.append(order)

        returned_orders = list()
        all_fine = 0  # 总罚金
        for returned_order in returned_order_list:
            all_fine += returned_order.debt
            order = {
                'borrow_order_id': returned_order.order_id,
                "borrow_book_name": returned_order.book.the_book.book_name,
                "borrow_book_id": returned_order.book_id,
                "return_time": time_stamp_to_str(returned_order.return_time.timetuple()),
                "debt": returned_order.debt
            }
            returned_orders.append(order)

        # 交易记录
        money_orders = list()
        for money_order in money_order_list:
            order = {
                'id': money_order.id,
                "order_type": money_order.get_order_type_display(),
                "user_name": money_order.user.user_name,
                "order_time": time_stamp_to_str(money_order.order_time.timetuple()),
                "librarian": money_order.librarian.administrator_name,
                "num": money_order.num
            }
            money_orders.append(order)

        return JsonResponse(
                            {'result': True,
                             'user_message': user_dict,
                             'reserve_orders': reserve_orders,
                             'borrow_orders': borrow_orders,
                             'returned_orders': returned_orders,
                             'all_fine': all_fine,
                             'money_orders': money_orders
                             }
                            )
    except Exception as e:
        print(e)
        return JsonResponse({"result": False, "msg": "Error!"})


def add_book_api(request):
    '''
    添加图书
    :param request:
    :return:
    '''
    image_url = ""
    bar_code_url = ""
    if request.method == "POST":
        try:
            isbn = request.POST['isbn']
            try:
                if isbn != '':
                    temp = Book.objects.get(isbn=isbn)
                    if temp:
                        return JsonResponse({"result": False, 'msg': "The book already exists"})
            except Book.DoesNotExist:
                pass
            author = request.POST['author']
            book_name = request.POST['book_name']
            image_url = request.POST['image_url']
            total_num = request.POST['total_num']
            price = request.POST['price']
            type = request.POST["type"]
            place = request.POST['place']

            if image_url != '':
                image_result = requests.get(image_url)
                if image_result.status_code == 200:
                    with open("./librarian/static/book_image/%s.jpg" % isbn, "wb") as file:
                        file.write(image_result.content)
                image_url = '/static/book_image/%s.jpg' % isbn
            else:
                image_url = 'None'


            # -----------生成条形码示例-----------
            '''
            if isbn.isalnum() and isbn:
                result = BarCode.create_bar_code(isbn)
                if result[0]:
                    bar_code_url = result[2]
            '''
            # -----------##############----------

            book = Book()
            if isbn != '':
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
            else:
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
                all_book_list.append(AllBook(the_book=book, is_available=True))
            AllBook.objects.bulk_create(all_book_list)

            all = list(AllBook.objects.all())
            need = all[-int(total_num):]
            img_result = []
            img_str = ""
            for x in range(int(total_num)):
                # -----------生成条形码示例-----------

                result = BarCode.create_bar_code(need[x].book_id)
                if result[0]:
                    img_result.append(result[2])
                    img_str+="!"
                    img_str+=result[2]
                # -----------##############----------
        except Exception as e:
            return JsonResponse({'result': False, "msg": "Database save failed"})

    return JsonResponse({'result': True, 'book_image': image_url, 'bar_code_url': bar_code_url,
                         "book_list": img_str})


def bar_code_page(request):
    need = []
    if request.method == "GET":
        str = request.GET["book"]
        need = str.split("!")
    return render(request, 'book_barcode.html', {"book_list": need})


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
            response = JsonResponse({'result': True, 'id': book.id,'isbn': isbn, "price": book.price,
                                     'author': book.author, 'book_name': book.book_name,
                                     'place': book.place, "total_num": book.total_num,
                                     'type': book.type
                                     })
            return response

    else:
        return HttpResponseRedirect(reverse("index"))


def get_book_byid(request):
    '''
    获取书的信息
    :param request:
    :return:
    '''
    username = request.session.get('username', "None")
    if username == 'root':
        if request.method == "GET":
            isbn = request.GET["bookid"]

            try:
                book = Book.objects.get(id=isbn)
            except:
                return JsonResponse({"result": False})
            response = JsonResponse({'result': True, 'isbn': book.isbn, "price": book.price,
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
                id = request.GET["bookid"]
                isbn = request.GET["isbn"]
                #book = Book.objects.filter(isbn=isbn).first()
                book = Book.objects.get(id=id)
                total_num = request.GET["total_num"]
                place = request.GET['place']
                type = request.GET['type']
                img_str = ""
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
                                    all_book_list.append(AllBook(the_book=book, is_available=True))
                                AllBook.objects.bulk_create(all_book_list)
                                book.total_num = total_num
                                book.available_num += add_num

                                all = list(AllBook.objects.all())
                                need = all[-int(add_num):]
                                img_result = []
                                for x in range(int(add_num)):
                                    # -----------生成条形码示例-----------

                                    result = BarCode.create_bar_code(need[x].book_id)
                                    if result[0]:
                                        img_result.append(result[2])
                                        img_str += "!"
                                        img_str += result[2]
                                    # -----------##############----------

                            except:
                                pass
                        else:
                            response = JsonResponse({'result': False, "msg": "The quantity should not be less than the previous quantity."})
                            return response
                    book.save()
                    response = JsonResponse({'result': True,"book_list":img_str,"num":add_num})
                else:
                    response = JsonResponse({'result': False, "msg": "Unknown Error!"})
                return response
    else:
        return HttpResponseRedirect(reverse("index"))


def get_book_info_by_id_api(request):
    book_id = request.GET.get('book_id', None)
    result_json = {}
    if book_id:
        try:
            the_book = AllBook.objects.get(book_id=book_id)
            book = Book.objects.get(id=the_book.the_book.id)
            result_json['isbn'] = book.isbn
            result_json['author'] = book.author
            result_json['book_name'] = book.book_name
            result_json['result'] = True

        except:
            result_json['result'] = False
            result_json["msg"] = "Database operated failed!"  # 数据库操作失败！

        return JsonResponse(result_json)

    else:
        return JsonResponse({"result": False})


# 管理员查找删书记录
def search_del_history_api(request):
    if request.method != "POST":
        return JsonResponse({"result": False, "msg": "Forbidden"})
    username = request.session.get('username', "None")
    if not username == 'root':
        return JsonResponse({"result": False, "msg": "Forbidden"})
    try:
        title = request.POST["book_title"]
        del_history_list = BookDelHistory.objects.filter(book_name__contains=title).order_by('-deleted_time')
        #  del_history_list = BookDelHistory.objects.filter(book_isbn=isbn).order_by('-deleted_time')

        del_historys = list()
        for del_history in del_history_list:
            history = {
                "book_id": del_history.book_id,
                "book_name": del_history.book_name,
                "book_isbn": del_history.book_isbn,
                "deleted_time": time_stamp_to_str(del_history.deleted_time.timetuple()),
                "del_reason": del_history.get_del_reason_display(),
                "librarian_name": del_history.librarian.administrator_name
            }
            del_historys.append(history)

        return JsonResponse({'result': True, 'del_historys': del_historys})
    except Exception:
        return JsonResponse({"result": False, "msg": "Error!"})


# 发布新的通知
def add_new_notice(request):

    if request.method == "POST":
        try:
            title = request.POST["title"]
            content = request.POST["content"]
            author_name = request.POST['author_name']
            librarian = Administrator.objects.get(administrator_name=author_name)
            if librarian:
                Notice.objects.create(author=librarian, title=title, content=content)
                response = JsonResponse({'result': True})
            else:
                response = JsonResponse({'result': False, 'mag': 'db error!'})
            return response
        except:
            return JsonResponse({'result': False, 'msg': 'Error!'})


# 跳转到编辑通知页面
def edit_notice(request, notice_id):
    username = request.session.get('username', "None")
    if username == 'root':
        librarian_name = request.session['admin_name']

        librarian = Administrator.objects.get(administrator_name=librarian_name)
        notice = Notice.objects.get(id=notice_id)

        return render(request, 'edit_news.html', {'notice': notice, 'librarian': librarian})

    else:
        return HttpResponseRedirect(reverse("index"))


# 数据库编辑通知
def edit_notice_api(request):
    if request.method == "POST":
        try:
            notice_id = request.POST["notice_id"]
            title = request.POST["title"]
            content = request.POST["content"]
            author_name = request.POST['author_name']
            notice = Notice.objects.get(id=notice_id)
            librarian = Administrator.objects.get(administrator_name=author_name)
            if librarian and notice:
                notice.title = title
                notice.author = librarian
                notice.content = content
                notice.save()
                response = JsonResponse({'result': True})
            else:
                response = JsonResponse({'result': False, 'mag': 'db error!'})
            return response
        except:
            return JsonResponse({'result': False, 'msg': 'Error!'})


# 数据库删除通知
def delete_notice_api(request):
    if request.method != "POST":
        return JsonResponse({"result": False, "msg": "Forbidden"})
    username = request.session.get('username', "None")
    if not username == 'root':
        return JsonResponse({"result": False, "msg": "Forbidden"})
    try:
        notice_id = request.POST["notice_id"]
    except:
        return JsonResponse({"result": False, "msg": "Forbidden"})
    try:
        try:
            Notice.objects.get(id=notice_id).delete()
        except:
            return JsonResponse({"result": False, "msg": "Error!"})

        return JsonResponse({"result": True})
    except Exception:
        return JsonResponse({"result": False, "msg": "Error!"})


def search_notices_api(request):
    if request.method != "POST":
        return JsonResponse({"result": False, "msg": "Forbidden"})
    username = request.session.get('username', "None")
    if not username == 'root':
        return JsonResponse({"result": False, "msg": "Forbidden"})
    try:
        title = request.POST["title"]

        notice_list = Notice.objects.filter(title__contains=title).order_by('-updated_time')

        notices = list()
        for notice in notice_list:
            search_notice = {
                "id": notice.id,
                "title": notice.title,
                "content": notice.content,
                "updated_time": time_stamp_to_str(notice.updated_time.timetuple()),
                "librarian_name": notice.author.administrator_name
            }
            notices.append(search_notice)

        return JsonResponse({'result': True, 'notices': notices})
    except Exception:
        return JsonResponse({"result": False, "msg": "Error!"})


# 查看通知正文
def view_notice_content(request, notice_id):
    notice = Notice.objects.get(id=notice_id)
    username = request.session.get('username', "None")
    if username == "None":
        return HttpResponseRedirect(reverse("login"))
    return render(request, 'view_news.html', {"notice": notice, "username": username})


# 查找指定月 周 日的收入
def search_income_record_api(request):
    if request.method != "POST":
        return JsonResponse({"result": False, "msg": "Forbidden"})
    username = request.session.get('username', "None")
    if not username == 'root':
        return JsonResponse({"result": False, "msg": "Forbidden"})
    try:
        date1 = request.POST["date"]
        way = request.POST["way"]

        year = int(date1.split('-')[0])
        month = int(date1.split('-')[1])
        day = int(date1.split('-')[2])

        d = datetime.datetime(year, month, day)

        if way == 'day':
            income_record_list = MoneyOrder.objects.filter(
                order_time__year=d.year, order_time__month=d.month, order_time__day=d.day).order_by('-order_time')
        elif way == 'month':
            income_record_list = MoneyOrder.objects.filter(
                order_time__year=d.year, order_time__month=d.month).order_by('-order_time')
        elif way == 'week':
            week_start = d - datetime.timedelta(days=d.weekday())
            week_end = week_start + datetime.timedelta(days=7)
            income_record_list = MoneyOrder.objects.filter(
                order_time__range=[week_start, week_end]).order_by('-order_time')
        else:
            return JsonResponse({"result": False, "msg": "Error!"})

        income_records = list()
        income_num = 0
        income_fine = 0
        income_deposit = 0

        for incomerecord in income_record_list:
            income_num += incomerecord.num
            if incomerecord.order_type == 'D':
                income_deposit += incomerecord.num
            else:
                income_fine += incomerecord.num

            record = {
                "id": incomerecord.id,
                "user_name": incomerecord.user.user_name,
                "order_time": time_stamp_to_str(incomerecord.order_time.timetuple()),
                "order_type": incomerecord.get_order_type_display(),
                "librarian_name": incomerecord.librarian.administrator_name,
                "num": incomerecord.num
            }
            income_records.append(record)

        income_num = '%.2f' % income_num
        income_deposit = '%.2f' % income_deposit
        income_fine = '%.2f' % income_fine
        return JsonResponse({'result': True, 'income_records': income_records, 'income_num': income_num,
                             'income_deposit': income_deposit, 'income_fine': income_fine})
    except Exception:
        return JsonResponse({"result": False, "msg": "Error!"})