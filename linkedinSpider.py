


# encoding=utf-8
# ----------------------------------------
# 语言：Python2.7
# 日期：2017-03-24
# 作者：九茶<http://blog.csdn.net/bone_ace>
# 功能：根据公司名称抓取员工的LinkedIn数据
# ----------------------------------------

import sys
import copy
from urllib import unquote
import requests
from urllib import quote
import re
from lxml import etree
import pymysql
import time
import random
import datetime

"""
    conn = pymysql.connect(host='127.0.0.1', user='root', password='123456', db='company',charset="utf8")

    cur = conn.cursor()

    sqlc = '''
                create table coffee(
                id int(11) not null auto_increment primary key,
                name varchar(255) not null,
                price float not null)DEFAULT CHARSET=utf8;

        A = cur.execute(sqlc)
        conn.commit()




        sqla = '''
        insert into  coffee(name,price)
        values(%s,%s);
       '''
        try:
            B = cur.execute(sqla,(g[1],g[0]))
            conn.commit()
            print('success')
        except:
            print("failue")

    conn.commit()
    cur.close()
    conn.close()

"""

reload(sys)
sys.setdefaultencoding('utf8')

CREDIT_GRADE = {  # 芝麻信用
    'EXCELLENT': '极好',
    'VERY_GOOD': '优秀',
    'GOOD': '良好',
    'ACCEPTABLE': '中等',
    'POOR': '较差'
}
LINKS_FINISHED = []  # 已抓取的linkedin用户


def login(laccount, lpassword):
    """ 根据账号密码登录linkedin """
    s = requests.Session()
    r = s.get('https://www.linkedin.com/uas/login')
    tree = etree.HTML(r.content)
    loginCsrfParam = ''.join(tree.xpath('//input[@id="loginCsrfParam-login"]/@value'))
    csrfToken = ''.join(tree.xpath('//input[@id="csrfToken-login"]/@value'))
    sourceAlias = ''.join(tree.xpath('//input[@id="sourceAlias-login"]/@value'))
    isJsEnabled = ''.join(tree.xpath('//input[@name="isJsEnabled"]/@value'))
    source_app = ''.join(tree.xpath('//input[@name="source_app"]/@value'))
    tryCount = ''.join(tree.xpath('//input[@id="tryCount"]/@value'))
    clickedSuggestion = ''.join(tree.xpath('//input[@id="clickedSuggestion"]/@value'))
    signin = ''.join(tree.xpath('//input[@name="signin"]/@value'))
    session_redirect = ''.join(tree.xpath('//input[@name="session_redirect"]/@value'))
    trk = ''.join(tree.xpath('//input[@name="trk"]/@value'))
    fromEmail = ''.join(tree.xpath('//input[@name="fromEmail"]/@value'))

    payload = {
        'isJsEnabled': isJsEnabled,
        'source_app': source_app,
        'tryCount': tryCount,
        'clickedSuggestion': clickedSuggestion,
        'session_key': laccount,
        'session_password': lpassword,
        'signin': signin,
        'session_redirect': session_redirect,
        'trk': trk,
        'loginCsrfParam': loginCsrfParam,
        'fromEmail': fromEmail,
        'csrfToken': csrfToken,
        'sourceAlias': sourceAlias
    }
    s.post('https://www.linkedin.com/uas/login-submit', data=payload)
    return s


def get_linkedin_url(url, s):
    """ 百度搜索出来的是百度跳转链接，要从中提取出linkedin链接 """
    try:
        r = s.get(url, allow_redirects=False)
        if r.status_code == 302 and 'Location' in r.headers.keys() and 'linkedin.com/in/' in r.headers['Location']:
            return r.headers['Location']
    except Exception, e:
        print 'get linkedin url failed: %s' % url
    return ''


def parse(content, url):
    """ 解析一个员工的Linkedin主页 """
   

    s = ['','','','','','','','','','','','','','','','','','']
    global my_count

    content = unquote(content).replace('&quot;', '"')

    profile_txt = ' '.join(re.findall('(\{[^\{]*?profile\.Profile"[^\}]*?\})', content))
    firstname = re.findall('"firstName":"(.*?)"', profile_txt)
    lastname = re.findall('"lastName":"(.*?)"', profile_txt)
    if firstname and lastname:
        s[1] = '%s%s' % (lastname[0], firstname[0])
        s[0] = '%s' % url
        summary = re.findall('"summary":"(.*?)"', profile_txt)
        if summary:
            s[2] = '%s' % summary[0]

        occupation = re.findall('"headline":"(.*?)"', profile_txt)
        if occupation:
            s[3] = '%s' % occupation[0]

        locationName = re.findall('"locationName":"(.*?)"', profile_txt)
        if locationName:
            s[4] = '%s' % locationName[0]

        networkInfo_txt = ' '.join(re.findall('(\{[^\{]*?profile\.ProfileNetworkInfo"[^\}]*?\})', content))
        connectionsCount = re.findall('"connectionsCount":(\d+)', networkInfo_txt)
        if connectionsCount:
            s[5] = '%s' % connectionsCount[0]

        sesameCredit_txt = ' '.join(re.findall('(\{[^\{]*?profile\.SesameCreditGradeInfo"[^\}]*?\})', content))
        credit_lastModifiedAt = re.findall('"lastModifiedAt":(\d+)', sesameCredit_txt)
        credit_grade = re.findall('"grade":"(.*?)"', sesameCredit_txt)
        if credit_grade and credit_grade[0] in CREDIT_GRADE.keys():
            credit_lastModifiedAt_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(credit_lastModifiedAt[0][:10]))) if credit_lastModifiedAt else ''
            s[6] = '%s %s' % (CREDIT_GRADE[credit_grade[0]], '   最后更新时间: %s' % credit_lastModifiedAt_date if credit_lastModifiedAt_date else '')
        wechat_txt = ' '.join(re.findall('(\{[^\{]*?profile\.WeChatContactInfo"[^\}]*?\})', content))
        wechat_image = re.findall('"qrCodeImageUrl":"(http.*?)"', wechat_txt)
        wechat_name = re.findall('"name":"(.*?)"', wechat_txt)
        if wechat_name:
            s[7] = '微信昵称: %s %s' % (wechat_name[0], '    二维码(链接): %s' % wechat_image[0].replace('&#61;', '=').replace('&amp;', '&') if wechat_image else '')
        elif wechat_image:
            s[8] = '微信二维码(链接): %s' % wechat_image[0].replace('&#61;', '')

        website_txt = ' '.join(re.findall('("included":.*?profile\.StandardWebsite",.*?\})', content))
        website = re.findall('"url":"(.*?)"', website_txt)
        if website:
            s[9] = '个人网站: %s' % website[0]

        educations = re.findall('(\{[^\{]*?profile\.Education"[^\}]*?\})', content)
        for one in educations:
            schoolName = re.findall('"schoolName":"(.*?)"', one)
            fieldOfStudy = re.findall('"fieldOfStudy":"(.*?)"', one)
            degreeName = re.findall('"degreeName":"(.*?)"', one)
            timePeriod = re.findall('"timePeriod":"(.*?)"', one)
            schoolTime = ''
            if timePeriod:
                startdate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,startDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                enddate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,endDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                start_year = re.findall('"year":(\d+)', startdate_txt)
                start_month = re.findall('"month":(\d+)', startdate_txt)
                end_year = re.findall('"year":(\d+)', enddate_txt)
                end_month = re.findall('"month":(\d+)', enddate_txt)
                startdate = ''
                if start_year:
                    startdate += '%s' % start_year[0]
                    if start_month:
                        startdate += '.%s' % start_month[0]
                enddate = ''
                if end_year:
                    enddate += '%s' % end_year[0]
                    if end_month:
                        enddate += '.%s' % end_month[0]
                if len(startdate) > 0 and len(enddate) == 0:
                    enddate = '现在'
                schoolTime += '   %s ~ %s' % (startdate, enddate)
            if schoolName:
                fieldOfStudy = '   %s' % fieldOfStudy[0] if fieldOfStudy else ''
                degreeName = '   %s' % degreeName[0] if degreeName else ''
            s[10] = s[10] + '%s %s %s %s  |' % (schoolName[0], schoolTime, fieldOfStudy, degreeName)

        position = re.findall('(\{[^\{]*?profile\.Position"[^\}]*?\})', content)
        for one in position:
            companyName = re.findall('"companyName":"(.*?)"', one)
            title = re.findall('"title":"(.*?)"', one)
            locationName = re.findall('"locationName":"(.*?)"', one)
            timePeriod = re.findall('"timePeriod":"(.*?)"', one)
            positionTime = ''
            if timePeriod:
                startdate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,startDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                enddate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,endDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                start_year = re.findall('"year":(\d+)', startdate_txt)
                start_month = re.findall('"month":(\d+)', startdate_txt)
                end_year = re.findall('"year":(\d+)', enddate_txt)
                end_month = re.findall('"month":(\d+)', enddate_txt)
                startdate = ''
                if start_year:
                    startdate += '%s' % start_year[0]
                    if start_month:
                        startdate += '.%s' % start_month[0]
                enddate = ''
                if end_year:
                    enddate += '%s' % end_year[0]
                    if end_month:
                        enddate += '.%s' % end_month[0]
                if len(startdate) > 0 and len(enddate) == 0:
                    enddate = '现在'
                positionTime += '   %s ~ %s' % (startdate, enddate)
            if companyName:
                title = '   %s' % title[0] if title else ''
                locationName = '   %s' % locationName[0] if locationName else ''
                s[11] = s[11] + '%s %s %s %s  |' % (companyName[0], positionTime, title, locationName)
                title_now = title

        publication = re.findall('(\{[^\{]*?profile\.Publication"[^\}]*?\})', content)
        for one in publication:
            name = re.findall('"name":"(.*?)"', one)
            publisher = re.findall('"publisher":"(.*?)"', one)
            if name:
                s[12] = s[12] + '%s %s  ' % (name[0], '   出版社: %s' % publisher[0] if publisher else '')

        honor = re.findall('(\{[^\{]*?profile\.Honor"[^\}]*?\})', content)
        for one in honor:
            title = re.findall('"title":"(.*?)"', one)
            issuer = re.findall('"issuer":"(.*?)"', one)
            issueDate = re.findall('"issueDate":"(.*?)"', one)
            issueTime = ''
            if issueDate:
                issueDate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s"[^\}]*?\})' % issueDate[0].replace('(', '\(').replace(')', '\)'), content))
                year = re.findall('"year":(\d+)', issueDate_txt)
                month = re.findall('"month":(\d+)', issueDate_txt)
                if year:
                    issueTime += '   发行时间: %s' % year[0]
                    if month:
                        issueTime += '.%s' % month[0]
            if title:
                s[13] = s[13] + '%s %s %s  ' % (title[0], '   发行人: %s' % issuer[0] if issuer else '', issueTime)

        organization = re.findall('(\{[^\{]*?profile\.Organization"[^\}]*?\})', content)
        for one in organization:
            name = re.findall('"name":"(.*?)"', one)
            timePeriod = re.findall('"timePeriod":"(.*?)"', one)
            organizationTime = ''
            if timePeriod:
                startdate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,startDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                enddate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,endDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                start_year = re.findall('"year":(\d+)', startdate_txt)
                start_month = re.findall('"month":(\d+)', startdate_txt)
                end_year = re.findall('"year":(\d+)', enddate_txt)
                end_month = re.findall('"month":(\d+)', enddate_txt)
                startdate = ''
                if start_year:
                    startdate += '%s' % start_year[0]
                    if start_month:
                        startdate += '.%s' % start_month[0]
                enddate = ''
                if end_year:
                    enddate += '%s' % end_year[0]
                    if end_month:
                        enddate += '.%s' % end_month[0]
                if len(startdate) > 0 and len(enddate) == 0:
                    enddate = '现在'
                organizationTime += '   %s ~ %s' % (startdate, enddate)
            if name:
                s[14] = s[14] + '%s %s  ' % (name[0], organizationTime)

        patent = re.findall('(\{[^\{]*?profile\.Patent"[^\}]*?\})', content)
        for one in patent:
            title = re.findall('"title":"(.*?)"', one)
            issuer = re.findall('"issuer":"(.*?)"', one)
            url = re.findall('"url":"(http.*?)"', one)
            number = re.findall('"number":"(.*?)"', one)
            localizedIssuerCountryName = re.findall('"localizedIssuerCountryName":"(.*?)"', one)
            issueDate = re.findall('"issueDate":"(.*?)"', one)
            patentTime = ''
            if issueDate:
                issueDate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s"[^\}]*?\})' % issueDate[0].replace('(', '\(').replace(')', '\)'), content))
                year = re.findall('"year":(\d+)', issueDate_txt)
                month = re.findall('"month":(\d+)', issueDate_txt)
                day = re.findall('"day":(\d+)', issueDate_txt)
                if year:
                    patentTime += '   发行时间: %s' % year[0]
                    if month:
                        patentTime += '.%s' % month[0]
                        if day:
                            patentTime += '.%s' % day[0]
            if title:
                s[15] = s[15] + '%s %s %s %s %s %s  ' % (title[0], '   发行者: %s' % issuer[0] if issuer else '', '   专利号: %s' % number[0] if number else '', '   所在国家: %s' % localizedIssuerCountryName[0] if localizedIssuerCountryName else '', patentTime, '   专利详情页: %s' % url[0] if url else '')

        project = re.findall('(\{[^\{]*?profile\.Project"[^\}]*?\})', content)
        for one in project:
            title = re.findall('"title":"(.*?)"', one)
            description = re.findall('"description":"(.*?)"', one)
            timePeriod = re.findall('"timePeriod":"(.*?)"', one)
            projectTime = ''
            if timePeriod:
                startdate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,startDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                enddate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,endDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                start_year = re.findall('"year":(\d+)', startdate_txt)
                start_month = re.findall('"month":(\d+)', startdate_txt)
                end_year = re.findall('"year":(\d+)', enddate_txt)
                end_month = re.findall('"month":(\d+)', enddate_txt)
                startdate = ''
                if start_year:
                    startdate += '%s' % start_year[0]
                    if start_month:
                        startdate += '.%s' % start_month[0]
                enddate = ''
                if end_year:
                    enddate += '%s' % end_year[0]
                    if end_month:
                        enddate += '.%s' % end_month[0]
                if len(startdate) > 0 and len(enddate) == 0:
                    enddate = '现在'
                projectTime += '   时间: %s ~ %s' % (startdate, enddate)
            if title:
                s[16] = s[16] + '%s %s %s' % (title[0], projectTime, '   项目描述: %s' % description[0] if description else '')

        volunteer = re.findall('(\{[^\{]*?profile\.VolunteerExperience"[^\}]*?\})', content)
        for one in volunteer:
            companyName = re.findall('"companyName":"(.*?)"', one)
            role = re.findall('"role":"(.*?)"', one)
            timePeriod = re.findall('"timePeriod":"(.*?)"', one)
            volunteerTime = ''
            if timePeriod:
                startdate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,startDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                enddate_txt = ' '.join(re.findall('(\{[^\{]*?"\$id":"%s,endDate"[^\}]*?\})' % timePeriod[0].replace('(', '\(').replace(')', '\)'), content))
                start_year = re.findall('"year":(\d+)', startdate_txt)
                start_month = re.findall('"month":(\d+)', startdate_txt)
                end_year = re.findall('"year":(\d+)', enddate_txt)
                end_month = re.findall('"month":(\d+)', enddate_txt)
                startdate = ''
                if start_year:
                    startdate += '%s' % start_year[0]
                    if start_month:
                        startdate += '.%s' % start_month[0]
                enddate = ''
                if end_year:
                    enddate += '%s' % end_year[0]
                    if end_month:
                        enddate += '.%s' % end_month[0]
                if len(startdate) > 0 and len(enddate) == 0:
                    enddate = '现在'
                volunteerTime += '   时间: %s ~ %s' % (startdate, enddate)
            if companyName:
                s[17] = s[17] + '%s %s %s' % (companyName[0], volunteerTime, '   角色: %s' % role[0] if role else '')

        sqla_fix = "insert into %s" % company_name

        sqla = sqla_fix + '''
                (头衔, 姓名, 领英主页, 简介, 身份职位, 坐标, 好友人数, 芝麻信用, 微信昵称, 微信二维码, 个人网站, 教育经历, 工作经历, 出版作品, 荣誉奖项, 参与组织, 专利发明, 所做项目, 志愿者经历)
                values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
               '''

        try:
            B = cur.execute(sqla, (title_now, s[1], s[0], s[2], s[3], s[4], s[5], s[6], s[7], s[8], s[9], s[10], s[11], s[12], s[13], s[14], s[15], s[16], s[17]))
            conn.commit()
            print('success')
            my_count = my_count + 1
            print my_count
        except:
            print('failure')

    print '\n\n'


def crawl(url, s, index):
    """ 抓取每一个搜索结果 """
    global failure_time
    try:
        if index == 1:
            url = get_linkedin_url(url, copy.deepcopy(s)).replace('cn.linkedin.com', 'www.linkedin.com')  # 百度搜索出的结果是百度跳转链接，要提取出linkedin的链接。
        if len(url) > 0 and url not in LINKS_FINISHED:
            LINKS_FINISHED.append(url)

            
            while True:
                try:
                    print 'sleep'
                    stop_second = random.randint(13,25)
                    print ('start sleep ' + '20')
                    time.sleep(stop_second)
                    stop_hour = random.randint(0, 100)
                    if stop_hour > 70:
                        print ('start sleep ' + '200')
                        time.sleep(200)
                    if stop_hour > 98:
                        print ('start sleep ' + '800')
                        time.sleep(800)
                    now = datetime.datetime.now()
                    if now.hour == 1 or now.hour == 13:
                        print ('start sleep 3 hour')
                        time.sleep(18000)
                    r = s.get(url, timeout=10)
                except Exception, e:
                    failure_time += 1
                    break
                if r.status_code == 200:
                    parse(r.content, url)
                    break
                else:
                    print '%s %s' % (r.status_code, url)
                    failure_time += 1
                    break
            if failure_time >= 5:
                print 'Failed: %s' % url
		
    except Exception, e:
        pass


if __name__ == '__main__':
    s = login(sys.argv[1], sys.argv[2])  # 测试账号
    # Company_Name = ['中国平安', '中国人寿', '中国人保财险', '中国人保寿险', '中国太平洋保险', '友邦保险', '新华保险', '泰康保险', '安邦保险', '阳光保险', '大地财险',
    #                 '富德生命人寿', '华夏人寿', '珠江人寿', '辛福人事', '中意人寿', '中国再保险', '华泰保险']
    Company_Name = ['中国平安', '中国人寿', '中国人保财险', '中国人保寿险', '中国太平洋保险', '友邦保险']
    Title_Now = ['人事', '行政', '销售', '会计', '精算', '经理', '金融', '客户', '产品', '财务', 'IT', '行政', '风控', '投资',
                 '保险', '核赔', '审计', '总监']
    # company_name = raw_input('Input the company you want to crawl:')
    # title_now = raw_input('Input the title of whom you want to crawl:')
    failure_time = 0
    change_login_threshold = 0
    exist_page = 0
    try:
	file = open('历史记录', 'r')
    	for line in file:
        	exist_page += line.count('true', 0, len(line))
    except:
	file = open('历史记录', 'w')
    file.close()
    for company_name in Company_Name:
        # 启动mySQL
        conn = pymysql.connect(host='192.168.61.43', user='redwolf', password='123456', db='company', charset="utf8")
        cur = conn.cursor()
        sqlc = '''
                                    create table %s(
                                    id int(11) not null auto_increment primary key,
                                    头衔 varchar(15),
                                    姓名 varchar(255),
                                    领英主页 varchar(255),
                                    简介 varchar(255),
                                    身份职位 varchar(255),
                                    坐标 varchar(255),
                                    好友人数 varchar(255),
                                    芝麻信用 varchar(255),
                                    微信昵称 varchar(255),
                                    微信二维码 varchar(255),
                                    个人网站 varchar(255),
                                    教育经历 varchar(255),
                                    工作经历 varchar(255),
                                    出版作品 varchar(255),
                                    荣誉奖项 varchar(255),
                                    参与组织 varchar(255),
                                    专利发明 varchar(255),
                                    所做项目 varchar(255),
                                    志愿者经历 varchar(255))DEFAULT CHARSET=utf8;
                                    ''' % company_name
        try:
            A = cur.execute(sqlc)
            conn.commit()
            print('success')
        except:
            print("failue")

        for title_now in Title_Now:
            my_count = 0
            maxpage = 2  # 抓取前50页百度搜索结果，百度搜索最多显示76页
            

            # 百度搜索
            url = 'http://www.baidu.com/s?ie=UTF-8&wd=%20%7C%20领英%20' + quote(company_name) + '%20+%20' + quote(title_now) + '%20site%3Alinkedin.com'
            failure = 0
            while len(url) > 0 and failure < 10:
                try:
                    r = requests.get(url, timeout=30)
                except Exception, e:
                    failure += 1
                    continue
                if r.status_code == 200:
                    if exist_page == 0:
                        change_login_threshold += 1
                        if change_login_threshold > 2:
                            sys.exit(0)
                        hrefs = list(set(re.findall('"(http://www\.baidu\.com/link\?url=.*?)"', r.content)))  # 一页有10个搜索结果
                        for href in hrefs:
                            n = s.get(href, timeout = 30)
                            hrefs2 = list(set(re.findall('"(https://www\.linkedin\.com/in.*?)"', n.content)))  # 一页有10个搜索结果
                            for href2 in hrefs2:
                                crawl(href2, copy.deepcopy(s), 0)
                        for href in hrefs:
                            crawl(href, copy.deepcopy(s), 1)
                        file = open('历史记录', 'a')
                        file.write('true')
                        file.close()
                    else:
                        exist_page -= 1
                    tree = etree.HTML(r.content)
                    nextpage_txt = tree.xpath('//div[@id="page"]/a[@class="n" and contains(text(), "下一页")]/@href'.decode('utf8'))
                    url = 'http://www.baidu.com' + nextpage_txt[0].strip() if nextpage_txt else ''
                    failure = 0
                    maxpage -= 1
                    if maxpage <= 0:
                        break
                else:
                    failure += 2
                    print 'search failed: %s' % r.status_code
            if failure >= 10:
                print 'search failed: %s' % url

