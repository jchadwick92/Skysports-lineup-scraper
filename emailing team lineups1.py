import datetime
from bs4 import BeautifulSoup
from urllib.request import urlopen
import re
import time
import smtplib
import sqlite3
import xlrd

my_url = 'http://www.skysports.com/premier-league-fixtures'


def delete_update_salaries():
    book = xlrd.open_workbook('Yahoo_DF_player_export.xls')
    sheet = book.sheet_by_name('Yahoo_DF_player_export')
    conn = sqlite3.connect('football_stats.db')
    c = conn.cursor()
    c.execute('DELETE FROM yahoo_salaries')
    conn.commit()
    for r in range(1, sheet.nrows):
        Id      = re.sub('[^0-9]', '', sheet.cell(r,0).value)
        First = sheet.cell(r,1).value
        Last          = sheet.cell(r,2).value
        Position     = sheet.cell(r,3).value
        Team       = sheet.cell(r,4).value
        Opponent = sheet.cell(r,5).value
        Game        = sheet.cell(r,6).value
        Time       = sheet.cell(r,7).value
        Salary     = sheet.cell(r,8).value
        FPPG        = sheet.cell(r,9).value
        Injury         = sheet.cell(r,10).value
      
        c.execute("""INSERT INTO yahoo_salaries(id, first_name, last_name, position, team, opponent, game, time, salary, fppg, injury_status)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (Id, First, Last, Position, Team, Opponent, Game, Time, Salary, FPPG, Injury))

    conn.commit()
    c.close()
    conn.close()


def create_expected_values():
    book = xlrd.open_workbook("Merged yahoo stats with IDs 1609.xlsx")
    sheet = book.sheet_by_name('Sheet2')
    conn = sqlite3.connect('football_stats.db')
    c = conn.cursor()
    c.execute('DELETE FROM projections')
    conn.commit()
    c.execute("""CREATE TABLE IF NOT EXISTS projections(ID INTEGER, name TEXT, expected_points REAL, value REAL)""")
    conn.commit()
    for r in range(1, sheet.nrows):
        ID      = re.sub('[^0-9]', '', sheet.cell(r,1).value)
        name = sheet.cell(r,0).value
        expected_points = sheet.cell(r,21).value
        value = sheet.cell(r,22).value

        c.execute("""INSERT INTO projections(ID, name, expected_points, value)VALUES (?, ?, ?, ?)""",
                  (ID, name, expected_points, value))
    conn.commit()
    c.close()
    conn.close()


def get_html(url):
    global soup
    Client = urlopen(url)
    page_html = Client.read()
    Client.close()
    soup = BeautifulSoup(page_html, 'html.parser')


def time_href():
    time_link = {}
    new_html = ''
    for tag in soup.find("h4").next_siblings:
        if tag.name == "h4":
            break
        else:
            new_html += str(tag)
    new_soup = BeautifulSoup(new_html, 'html.parser')   
    links = new_soup.findAll('a', href=re.compile('^http://www.skysports.com/football/'))
    for link in links:
        time = (link.find('span',{'class':'matches__date'}).text).strip()
        href = link.get('href')
        url_id = re.sub('[^0-9]','', href)
        team_url = href.rstrip('0123456789')
        href = team_url + 'teams/' + url_id
        time_link[href] = time
    return time_link


def team_lineup_link(): # checks time and then if within an hour of match, checks the lineup
    for link,ko in time_href().items():
        print(link)
        while True:
            d = datetime.datetime.now()
            current_time = '{:02d}{:02d}'.format((d.hour+1),d.minute)
            KO = ko.replace(':', '')
            if (int(current_time) - int(KO)) >= 100: # once the match has started
                print('Match has started')
                break
            if KO <= current_time: # if time is less than an hour before match
                get_html(link)
                try: # try to see if teams are not availble
                    print(1)
                    not_available = (soup.find('p', text='Team lineups are not available yet')).text
                except AttributeError:
                    not_available = False
                    print('teams available')
                finally:
                    if not_available == 'Team lineups are not available yet':
                        print('Team lineups are not available yet')
                        time.sleep(30)
                    else: # if lineups are available
                        print('Emailing lineups')
                        get_lineup()
                        break # breaks out of while loop when lineups are available
            else: # more than an hour before KO
                print('not time yet')
                print('{:02d}:{:02d}'.format((d.hour),d.minute))
                time.sleep(60)


def email(a, b, lineup_a, lineup_b):
    smtpObj = smtplib.SMTP('smtp.gmail.com', 587)
    smtpObj.ehlo()
    smtpObj.starttls()
    smtpObj.login('#', '#')
    smtpObj.sendmail('#', '#', 'Subject: %s vs %s \n\n%s \n\n%s' %(a, b, lineup_a, lineup_b))
    smtpObj.quit()


def get_lineup():
    sections = soup.findAll('div', {'class':'team-lineups__list-team'})
    team_name_A = (sections[0].h3.text)
    team_name_B = (sections[1].h3.text)

    players = sections[0].ul.findAll('li')
    team_lineup_A = ''
    for i in players[:11]:
        player = i.a.findAll('span')[1].text.strip()
        team_lineup_A += get_player_avg(player)
        
    players = sections[1].ul.findAll('li')
    team_lineup_B = ''
    for i in players[:11]:
        player = i.a.findAll('span')[1].text
        player = re.sub('\(c\)', '', player)
        player = player.strip()
        team_lineup_B += get_player_avg(player)

    email(team_name_A, team_name_B, team_lineup_A, team_lineup_B)


def get_player_avg(name):
    conn = sqlite3.connect('football_stats.db')
    c = conn.cursor()

    c.execute('SELECT id FROM idSkySportsName WHERE name=?', (name, ))
    try:
        ID = c.fetchone()[0]
    except TypeError:
        ID = 0
    if ID == 0:
        expected_pts = 'n/a'
        salary = 'n/a'
    else:
        c.execute('SELECT salary FROM yahoo_salaries WHERE id=?', (ID,))
        salary = c.fetchone()[0]
        c.execute('SELECT expected_points FROM projections WHERE id=?', (ID,))
        try:
            expected_pts = round(c.fetchone()[0], 2)
        except TypeError:
            c.execute('SELECT fppg FROM yahoo_salaries WHERE id=?', (ID,))
            try:
                expected_pts = c.fetchone()[0]
            except TypeError:
                expected_pts = 'n/a'
    if salary == 10:
        player_stats = '\n##' + name + '   ' + str(expected_pts) + '   ' + str(salary) + ' ##\n\n'
    else:
        player_stats = name + '    ' + str(expected_pts) + '    ' + str(salary) + '\n'
    c.close()
    conn.close()
    return player_stats

    
delete_update_salaries()
create_expected_values()
while True:
    if datetime.datetime.now() >= datetime.datetime(2017, 9, 23, 10, 30, 0, 0):
        get_html(my_url)
        team_lineup_link()
        break


