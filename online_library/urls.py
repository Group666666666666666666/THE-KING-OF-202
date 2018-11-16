"""online_library URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
import librarian.views as librarian_views
import reader.views as reader_views
import administrator.views as administrator_views
from django.views.static import serve
from django.conf import settings

urlpatterns = [
    # 网页 url
    url(r'^admin/', admin.site.urls),
    url(r'^$', librarian_views.index, name="index"),
    url(r'^login/$', reader_views.login, name="login"),
    url(r'^loginAdmin/$', administrator_views.login, name="admin_login"),
    url(r'^loginAdmin/manage/$', administrator_views.Adminlogin, name="admin_manage_login"),
    url(r'^loginAdminRoot/$', administrator_views.login_adminRoot, name="loginAdminRoot"),
    url(r'^manage/$', librarian_views.manager_page, name="manage_page"),
    url(r'^update_reader/$', librarian_views.update_reader_page, name="update_reader_page"),
    url(r'^change_passwd/$', reader_views.change_passwd_page, name="change_passwd"),
    # 图书详情
    url(r'^book_detail/$', librarian_views.book_detail, name="book_detail"),

    # 用户禁止注册 转由图书管理员注册读者 因而废弃该url
    # url(r'^register/$', reader_views.register, name="register"),
    # 媒体目录 访问 书的条形码
    url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    # url(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    # 下载书的条形码
    url(r'^download/(\d+)/$', librarian_views.download_book_bar_code_api, name="download_bar_code"),
    url(r'^clear_message/$', librarian_views.clear_message, name="logout"),
    url(r'^user_message/$', reader_views.user_message, name="user_message"),
    url(r'^add_book/$', librarian_views.add_book, name="add_book"),
    url(r'^search_book/$', librarian_views.search_book, name="search_book"),
    url(r'^add_barcode_page/$', librarian_views.bar_code_page, name="add_barcode_page"),
    url(r'^manager/delete_book/$', librarian_views.delete_book, name="manager_delete_book"),
    url(r'^manager/delete_record/$', librarian_views.del_record, name="manager_del_record"),
    url(r'^manager/delete_book/api/$', librarian_views.delete_book_api, name='delete_book_api'),
    url(r'^manager/post_news_record/$', librarian_views.post_news_record, name="manager_post_news_record"),
    # 单本信息
    url(r'^book_detail_api/$', librarian_views.book_detail_api, name="book_detail_api"),
    # 直接借书
    url(r'^borrow_book_directly_api/$', librarian_views.directly_borrow_book_api, name="borrow_book_directly_api"),



    url(r'^manager/income_record/$', librarian_views.income_record, name="manager_income_record"),
    url(r'^manager/add_reader/$', librarian_views.add_reader, name="manager_add_reader"),
    url(r'^manager/delete_reader/$', librarian_views.delete_reader, name="manager_delete_reader"),
    url(r'^manager/update_reader/$', librarian_views.update_reader, name="manager_update_reader"),
    url(r'^manager/update_readerByMe/$', librarian_views.update_readerByMe, name="manager_update_readerByMe"),
    url(r'^manager/update_readerByMeInfo/$', librarian_views.update_readerByMeInfo, name="manager_update_readerByMeInfo"),
    url(r'^manager/get_readerHis/$', librarian_views.get_reader_history, name="manager_get_readerHis"),
    url(r'^manager/get_adminPsw/$', administrator_views.get_adminPsw, name="manager_get_adminPsw"),
    url(r'^manager/update_book_message/$', librarian_views.update_book_message_page, name="update_book_message"),
    url(r'^manager/edit_type_location/$', librarian_views.edit_type_location_page, name="edit_type_location"),
    # tyr admin更新超级管理员密码
    url(r'^admin/change_passwd/$', administrator_views.admin_change_password, name='admin_change_passwd'),
    url(r'^manager/update_adminPsw/$', administrator_views.update_adminPsw, name="manager_update_adminPsw"),
    # tyr admin更新lib密码
    url(r'^manager/update_libPsw/$', administrator_views.update_lib, name="manager_get_updatelibPsw"),
    # api js 请求 url
    url(r'^manager/return_book/api/$', librarian_views.return_book_api, name="manage_return_book_api"),
    url(r'^manager/borrow_book/api/$', librarian_views.borrow_book_api, name="manage_borrow_book_api"),
    url(r'^manager/send_mail/api/$', librarian_views.send_mail_api, name="manage_send_mail_api"),
    url(r'^manager/user_message/api/$', librarian_views.manage_user_api, name="manage_user_message_api"),
    url(r'^manager_login/api/$', librarian_views.administrator_login_post, name="manage_login_api"),
    url(r'^test_user_name/api/$', reader_views.user_name_is_available, name="test_user_name_api"),
    url(r'^register/api/$', reader_views.register_post, name="register_api"),
    url(r'^login/api/$', reader_views.login_post, name="login_api"),
    url(r'^isbn/api/$', librarian_views.book_message_api, name="isbn_api"),
    url(r'^add_book/api/$', librarian_views.add_book_api, name="add_book_api"),
    url(r'^update_book/api/$', librarian_views.update_book, name="update_book_api"),
    url(r'^get_book/api/$', librarian_views.get_book, name="get_book_api"),
    url(r'^get_bookbyid/api/$', librarian_views.get_book_by_id, name="get_bookbyid_api"),
    url(r'^reserve/api/$', librarian_views.reserve_api, name="reserve_api"),
    url(r'^search_book/api/$', librarian_views.search_book_api, name="search_book_api"),
    url(r'^changePsw/api/$', reader_views.sendEmailToChangePsw, name="change_reader_psw"),
    url(r'^forgetpsw/$', reader_views.forget_passwd_page, name="forget_reader_psw"),
    url(r'^createLib/$', administrator_views.create_lib, name="create_lib"),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    # 系统管理员编辑图书管理员信息
    url(r'^manager/edit_librarian/(?P<librarian_name>[a-zA-Z0-9_]+)/$', administrator_views.edit_librarian, name="edit_librarian"),
    url(r'^manager/manager_edit_librarian/$', administrator_views.manager_edit_librarian,
        name="manager_edit_librarian"),
    # 系统管理员删除图书管理员
    url(r'^manager/delete_librarian/$', administrator_views.delete_librarian, name="delete_librarian"),
    # 系统管理员编辑图书馆罚金等规则
    url(r'^manager/edit_rules/$', administrator_views.edit_rules, name="edit_rules"),
    # 通过书id获得书的其他信息
    url(r'^get_book_info_by_id/api/$', librarian_views.get_book_info_by_id_api, name='get_book_info_by_id_api'),
    # 图书管理员缴纳罚金
    url(r'^manager/pay_debt/api/$', librarian_views.manager_pay_debt_api, name='manager_pay_debt_api'),
    # 图书管理员查找指定isbn的删除记录
    url(r'^manager/search_del_history/api/$', librarian_views.search_del_history_api, name='search_del_history_api'),
    # 图书管理员发布新的通知
    url(r'^manager/post_news/$', librarian_views.post_news, name="manager_post_news"),
    url(r'^manager/add_new_notice/api/$', librarian_views.add_new_notice, name="add_new_notice"),
    # 管理员编辑通知
    url(r'^manager/edit_notice/(?P<notice_id>\d+)/$', librarian_views.edit_notice, name="edit_notice"),
    url(r'^manager/edit_notice/api/$', librarian_views.edit_notice_api, name="edit_notice_api"),
    # 图书管理员删除通知
    url(r'^manager/delete_notice/api/$', librarian_views.delete_notice_api, name='delete_notice_api'),
    # 图书管理员通过标题查找通知
    url('^manager/search_notices/api/$', librarian_views.search_notices_api, name='search_notices_api'),
    # 查看通知正文
    url(r'^view_notice_content/(?P<notice_id>\d+)/$', librarian_views.view_notice_content, name="view_notice_content"),
    # 查找指定月、周、日的收入
    url(r'^manager/search_income_record/api/$', librarian_views.search_income_record_api,
        name="search_income_record_api"),
    # 用户取消预约订单
    url(r'^user/cancel_reserve/api/$', reader_views.cancel_reserve_api, name="cancel_reserve_api"),
    # 管理员添加类别和地点
    url(r'^manager/add_type_and_location/api', librarian_views.add_type_and_location_api,
        name='add_type_and_location_api'),
    # 管理员编辑类别和地点
    url(r'^manager/edit_type_and_location/api', librarian_views.edit_type_and_location_api,
        name='edit_type_and_location_api'),
    # 管理员删除类别和地点
    url(r'^manager/delete_type_and_location/api', librarian_views.delete_type_and_location_api,
        name='delete_type_and_location_api'),

]

