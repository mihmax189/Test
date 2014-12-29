#! /usr/bin/env python2

import os
import re
import requests
from lxml import html
from lxml import etree

class Request:

    def __init__(self):
        # Служебные данные для выполнения запроса
        self.iata_departure_str = ''
        self.iata_distanation_str = ''
        self.outboun_date_str = ''
        self.return_date_str = ''
        self.one_way_str = ''

    def check_date(self, date_str):
        '''
        Проверяет полученные от пользователя данные на корректность.
        '''
        if not re.match('^[0-9]{4}-[0-9]{2}-[0-9]{2}$', date_str):
            print 'The date must be entered in the format yyyy-mm-dd'
            return 1
        # проверка на корректность значений года, месяца, дня
        date_components_list = date_str.split('-')
        error_flag = 0
        if int(date_components_list[0]) < 2014:
            print 'You have specified an incorrect year: ', date_components_list[0]
            error_flag = 1
        if int(date_components_list[1]) > 12:
            print 'You have specified an incorrect month: ', date_components_list[1]
            error_flag = 1
        if int(date_components_list[2]) > 31:
            print 'You have specified an incorrect number: ', date_components_list[2]
            error_flag = 1
        if error_flag:
            return 2

        return 0

    def get_parametrs(self):
        '''
        Метод получает от пользователя IATA-коды аэропортов отправления и назначения,
        даты вылета и прибытия. Если дата возврата не задается, то параметр oneway
        принимает значение 1.
        '''
        print 'Please enter the following values: '
        self.iata_departure_str = self.iata_distanation_str = self.outboun_date_str = self.return_date_str = ''

        while len(self.iata_departure_str) == 0:
            self.iata_departure_str = raw_input('IATA-code airport of departure (AAA): ')
            # описание строки шаблона '^[A-Z]$': введенная информация должна состоять только
            # из трех латинских символов в верхнем регистре
            if not re.match('^[A-Z]{3}$', self.iata_departure_str):
                print 'IATA-code shell consist of three characters in uppercase'
                self.iata_departure_str = ''
        while len(self.iata_distanation_str) == 0:
            self.iata_distanation_str  = raw_input('Arrival airport: ')
            if not re.match('^[A-Z]{3}$', self.iata_distanation_str):
                print 'IATA-code shell consist of three characters in uppercase'
                self.iata_distanation_str = ''

        while len(self.outboun_date_str) == 0:
            self.outboun_date_str = raw_input('Departure date (yyyy-mm-dd): ')
            if self.check_date(self.outboun_date_str):
                outboun_date = ''
                continue

        # дата возврата может быть и не введена
        self.return_date_str  = raw_input('Arrival date: ')
        # если пользователь ввел дату возврата, то проверяем ее на корректность
        incorrect_date = False
        if len(self.return_date_str) != 0:
            incorrect_date = True

        while incorrect_date:
            self.return_date_str  = raw_input('Arrival date: ')
            if self.check_date(self.return_date_str):
                self.return_date_str = ''
                continue
            incorrect_date = False
        print 'Len return date: ', len(self.return_date_str)
        self.one_way_str = '1' if len(self.return_date_str) == 0 else '0'

    def get_requests_post(self):
        '''
        Формирует и выполняет запросы.
        '''
        with requests.session() as session:
            session = requests.Session()
            print 'Please, wait...'
            # Получить список аэропортов и соответствующие им IATA-коды
            # Анализ запросов сайта flyniki.com при помощи программы fiddler показал, что список аэропортов
            # и соответствующие им IATA-коды можно получить при помощи выполнения запроса GET по следующему
            # адресу
            url = 'http://www.flyniki.com/en-RU/site/json/suggestAirport.php?searchfor=departures&searchflightid=0&departures%5B%5D=&destinations%5B%5D=Graz&suggestsource%5B0%5D=activeairports&withcountries=0&withoutroutings=0&promotion%5Bid%5D=&promotion%5Btype%5D=&routesource%5B0%5D=airberlin&routesource%5B1%5D=partner'
            response = session.get(url)
            #print response.text

            response_json = response.json()
            # response_json представляет из себя словарь с единственным отображением ключа suggestList на список словарей
            # Сопоставить IATA-коды и имена аэропортов и извлечь их: получить доступ к элементу словаря response_join по
            # ключу suggestList. Пройтись по элементам (словарям) этого списка и произвести в них поиск значений (имен аэропортов)
            # по заданным IATA-кодам
            try:
                from_airport_name = [name[u'name'] for name in response_json[u'suggestList'] if name[u'code'] == self.iata_departure_str][0]
                to_airport_name = [name[u'name'] for name in response_json[u'suggestList'] if name[u'code'] == self.iata_distanation_str][0]
            except IndexError:
                print 'Invalid IATA-codes'
                exit(1)
            # debug info
            #print 'From name airport: ', from_airport_name
            #print 'To name airport: ', to_airport_name

            # формирование словаря атрибутов запроса
            info_for_requests = {'departure' : self.iata_departure_str, 'destination' : self.iata_distanation_str,
                                 'outboundDate' : self.outboun_date_str, 'returnDate' : self.return_date_str,
                                 'oneway' : self.one_way_str, 'openDateOverview' : '0', 'adultCount' : '1',
                                 'childCount' : '0', 'infantCount' : '0'}

            # Анализ запросов сайта flyniki.com при помощи программы fiddler показал, что для получения прайса
            # цен на конкретный рейс надо выполнить следующую последовательность запросов

            # запрос GET по адресу http://www.flyniki.com/en-RU/booking/flight/vacancy.php
            url = 'http://www.flyniki.com/en-RU/booking/flight/vacancy.php'
            # получение id сессии
            response = session.get(url, params=info_for_requests)

            # выстраиваем ajax форму, которая определяет информацию необходимую для обновления страницы (используем позиционные
            # аргументы для форматирования)
            _ajax_form = u'_ajax%5Btemplates%5D%5B%5D=form&_ajax%5Btemplates%5D%5B%5D=main&_ajax%5Btemplates%5D%5B%5D=priceoverview&'\
                u'_ajax%5Btemplates%5D%5B%5D=infos&_ajax%5BrequestParams%5D%5Bdeparture%5D={0}&_ajax%5BrequestParams'\
                u'%5D%5Bdestination%5D={1}&_ajax%5BrequestParams%5D%5BreturnDeparture%5D=&_ajax%5BrequestParams%5D%5BreturnDestination%5D='\
                u'&_ajax%5BrequestParams%5D%5BoutboundDate%5D={2}&_ajax%5BrequestParams%5D%5BreturnDate%5D={3}&_ajax%5BrequestParams'\
                u'%5D%5BadultCount%5D=1&_ajax%5BrequestParams%5D%5BchildCount%5D=0&_ajax%5BrequestParams%5D%5BinfantCount%5D=0&_ajax%5BrequestParams'\
                u'%5D%5BopenDateOverview%5D=&_ajax%5BrequestParams%5D%5Boneway%5D={4}'.format(from_airport_name, to_airport_name, self.outboun_date_str,
                                                                                           self.return_date_str, '' if self.one_way_str == '0' else 'on')
            print 'url: ', response.url
            headers = {'Referer' : response.url, 'Content-Type' : 'application/x-www-form-urlencoded'} # 'Referer' :
            # запрос POST для получения формы с результатами
            response = session.post(response.url, data=_ajax_form, headers=headers)
            #print 'response: ', response.text
            # response_json - представляет собой словарь с единственным ключом templates
            response_json = response.json()
            #print 'response_json: ', response_json
            page = html.document_fromstring(response_json['templates']['main'])

            # получаем элемент <div class='outbound block'> и извлекаем из него таблицу <table class='fligthtable'>
            tables_list = page.find_class('outbound block').pop().find_class('flighttable')
            if self.one_way_str == '0':
                # аналогично поступаем с элементом <div class='return block'>, если он есть
                tables_list.append(page.find_class('return block').pop().find_class('flighttable'))

            # теперь рассматриваем элементы извлеченных таблиц
            for table in tables_list:
                # извлекаем
                tbody = [el for el in table][1:]
                if len(tbody) == 0:
                    continue

                header_str_ = 'start/end Stops FlyDeal FlyClassic FlyFlex flight duration'
                print '='*len(header_str_)
                print header_str_
                for tr in tbody[0]:
            #        if tr.attrib['class'] == 'flightdetails':
            #            print '{0:>8}'.format(tr.getchildren()[0].getchildren()[1].getchildren()[1].text_content()
            #                                  .replace('\n', '').replace('\t', '').replace('duration of journey: ', ''))
            #            continue
            #        td_list = [td for td in tr][1:]
            #        time = [t for t in td_list]
            #        fly_deal = td_list[2].find_class('lowest').pop().text_content()
            #        fly_classic = td_list[3].find_class('lowest').pop().text_content()
            #        fly_flex = td_list[4].find_class('lowest').pop().text_content()
            #        print '{0}/{1}{2:>3}{3:>12}{4:>12}{5:>12}'.format(time[0].text, time[1].text,
            #                                                          td_list[1].text.replace('\n', '').replace('\t', ''),
            #                                                          fly_deal.replace('\n', '').replace('\t', ''),
            #                                                          fly_classic.replace('\n', '').replace('\t', ''),
            #                                                          fly_flex.replace('\n', '').replace('\t', '')),

def main():
    print 'This is main()'

#def main():
#    try:
#        request = Request()
#        request.get_parametrs()
#        request.get_requests_post()
#
#    except requests.ConnectionError:
#        print 'debug: Error http connection to www.flyniki.com!'
#        exit(1)

if __name__ == '__main__':
    main()
