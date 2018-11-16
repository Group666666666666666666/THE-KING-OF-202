from django.db import models
from reader.models import User
from administrator.models import Administrator


# 图书类别
class BookType(models.Model):
    book_type = models.CharField(max_length=50, null=False, unique=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)


# 图书位置
class BookLocation(models.Model):
    book_location = models.CharField(max_length=20, null=False, unique=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)


class Book(models.Model):
    author = models.CharField(max_length=50)
    isbn = models.IntegerField(null=True, unique=True)
    total_num = models.IntegerField(null=False)
    available_num = models.IntegerField(null=False)
    book_name = models.CharField(max_length=100, null=False)
    type = models.ForeignKey(BookType, related_name="books")
    place = models.ForeignKey(BookLocation, related_name="books")
    image_url = models.CharField(max_length=100, default='None')
    price = models.CharField(max_length=100, default='100')

    def __str__(self):
        return self.book_name


class AllBook(models.Model):
    book_id = models.IntegerField(auto_created=True, primary_key=True)
    is_available = models.BooleanField(null=False, default=True)
    the_book = models.ForeignKey(Book, related_name="all_book_isbn")
    # 0 可借 1 预约 2 已借 3 删除
    status = models.IntegerField(default=0)

    def __str__(self):
        return str(self.book_id)


class BorrowOrder(models.Model):
    order_id = models.IntegerField(auto_created=True, primary_key=True)
    user = models.ForeignKey(User, related_name="borrow_order_user")
    book = models.ForeignKey(AllBook, related_name="borrow_order_book")
    borrow_time = models.DateTimeField(null=False)
    debt = models.IntegerField(default=0)
    return_time = models.DateTimeField(null=True)
    is_return = models.BooleanField(null=False)
    # 判断借书是否到期
    expire = models.BooleanField(default=False)
    # 是否发送提示还书邮件
    is_alert = models.BooleanField(default=False)

    def __str__(self):
        return str(self.borrow_time)


class ReserveOrder(models.Model):
    order_id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(User, related_name="reserve_order_user")
    book = models.ForeignKey(AllBook, related_name="reserve_order_book")
    the_book = models.ForeignKey(Book, related_name="reserve_order_isbn")
    borrow_time = models.DateTimeField(null=False)
    successful = models.BooleanField(null=False)
    # 判断是否为历史订单 方便后期查找
    expire = models.BooleanField(default=False)

    def __str__(self):
        return str(self.user)


class Role(models.Model):
    books_limit = models.IntegerField()
    days_limit = models.IntegerField()
    deposit = models.IntegerField()
    fine = models.IntegerField()

    def __str__(self):
        return str(self.books_limit)


class Notice(models.Model):

    title = models.CharField(max_length=100)
    content = models.TextField(max_length=2000)
    author = models.ForeignKey(Administrator, related_name="notices",
                               null=True, on_delete=models.SET_NULL)
    issue_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.title)


# 图书馆收入记录
class MoneyOrder(models.Model):
    TYPE = (('D', 'DEPOSIT'), ('F', 'FINE'))

    user = models.ForeignKey(User, null=False, related_name="money_orders")
    order_type = models.CharField(max_length=1, choices=TYPE)
    num = models.FloatField(null=False)
    order_time = models.DateTimeField(null=False, auto_now_add=True)
    librarian = models.ForeignKey(Administrator, related_name='money_orders',
                                  null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return str(self.id)


# 用于每天自动更新一次数据库borrower表的debt，更新后添加一条数据
class AutoUpdateDB(models.Model):
    is_updated = models.BooleanField()
    updated_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


# 图书删除记录
class BookDelHistory(models.Model):
    REASON = (('D', 'DAMAGED'), ('L', 'LOST'))
    book_id = models.IntegerField()
    book_isbn = models.IntegerField(null=True)
    book_name = models.CharField(max_length=100)
    book_author = models.CharField(max_length=50)
    deleted_time = models.DateTimeField(auto_now_add=True)
    # 删除管理员时管理员设置为空
    librarian = models.ForeignKey(Administrator, related_name='deleted_books',
                                  null=True, on_delete=models.SET_NULL)
    del_reason = models.CharField(max_length=1, choices=REASON)

    def __str__(self):
        return str(self.id)




