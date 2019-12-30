import pandas as pd
import numpy as np
import sys
import pickle
import pdb
from pymongo import MongoClient
from collections import defaultdict
from scipy.stats import rankdata
import folium


def past_locations_map():
    m = folium.Map(location=[40, -98], zoom_start=5)

    folium.Marker([33.494171, -111.926048], popup='2018 - Scottsdale, AZ - Alex King 2019 - Scottsdale, AZ - Alex King').add_to(m)
    folium.Marker([36.805531, -114.06719], popup='2017 - Mesquite, NV - Alex King').add_to(m)
    folium.Marker([41.878114, -87.629798], popup='2016 - Chicago, IL - Jerry King').add_to(m)
    folium.Marker([34.502587, -84.951054], popup='2015 - Georgia - Stuart King').add_to(m)
    folium.Marker([42.331427, -83.045754], popup='2014 - Michigan - Reggie Sherrill').add_to(m)
    folium.Marker([39.739236, -104.990251], popup='2013 - Denver, CO - Stuart King').add_to(m)
    folium.Marker([47.677683, -116.780466], popup="2012 - Coeur d'Alene, ID - Jerry King").add_to(m)
    folium.Marker([37.096528, -113.568416], popup='2011 - St. George, UT - Reggie Sherrill').add_to(m)
    folium.Marker([38.291859, -122.458036], popup='2010 - Northern California - Alex King').add_to(m)
    folium.Marker([39.237685, -120.02658], popup='2009 - Lake Tahoe, CA - Alex King').add_to(m)
    folium.Marker([47.606209, -122.332071], popup='2008 - Seattle, WA - Alex King').add_to(m)
    folium.Marker([35.960638, -83.920739], popup='2007 - Tennessee - Stuart King').add_to(m)
    folium.Marker([33.520661, -86.80249], popup='2006 - Alabama - Gary Olson').add_to(m)
    folium.Marker([32.366805, -86.299969], popup='2005 - Alabama - Stuart King').add_to(m)

    m.save('templates/past_locations.html')


class Player(object):

    def __init__(self, name, hdcp, courses, skins=True):
        self.name = name
        self.skins = skins
        self.hdcp = hdcp
        self.scores = dict()
        self.net_scores = dict()
        self.courses = courses

        for course, (par, hdcps) in self.courses.items():
            self.create_scorecard(course)


    def create_scorecard(self, course):
        self.scores[course] = dict((x,0) for x in range(1,19))
        self.net_scores[course] = dict((x,0) for x in range(1,19))


    def post_score(self, course, hole, score, hdcp):
        self.scores[course][hole] = score

        par, hdcps = self.courses[course]
        hole_hdcp = hdcps[hole - 1]

        if hdcp > 18:
            super_hdcp = hdcp - 18
            if hole_hdcp <= super_hdcp:
                self.net_scores[course][hole] = score - 2
            else:
                self.net_scores[course][hole] = score - 1
        elif hole_hdcp <= hdcp:
            self.net_scores[course][hole] = score - 1
        elif hdcp < 0 and hole_hdcp <= abs(hdcp):
            self.net_scores[course][hole] = score + 1
        else:
            self.net_scores[course][hole] = score


    def show_scorecard(self, course, net=False):
        if net:
            return self.net_scores[course]

        return self.scores[course]


    def front_nine(self, course, net=False):
        if net:
            front = [v for k, v in self.net_scores[course].items()][:9]
            return front

        front = [v for k, v in self.scores[course].items()][:9]
        return front


    def back_nine(self, course, net=False):
        if net:
            back = [v for k,v in self.net_scores[course].items()][9:]
            return back

        back = [v for k, v in self.scores[course].items()][9:]
        return back


    def calc_course_score(self, course, net=False):
        if net:
            net_score = sum(self.net_scores[course].values())
            return net_score

        score = sum(self.scores[course].values())
        return score


    def calc_total_score(self, net=False):
        if net:
            total = 0
            for course in self.scores.keys():
                net_total += sum(self.net_scores[course].values())
            return net_total

        total = 0
        for course in self.scores.keys():
            total += sum(self.scores[course].values())
        return total


class PlayGolf(object):

    def __init__(self, year):
        self.year = year
        self.client = MongoClient()
        # self.client.drop_database('kc_2018')
        self.db = self.client['kc_{}'.format(year)] # Access/Initiate Database
        self.coll = self.db['scores'] # Access/Initiate Table
        self.courses = {
            "Lake Jovita - North" :
                ([5,3,4,3,4,5,4,4,4,5,4,4,3,4,5,4,3,4], [11,15,1,17,9,13,7,5,3,10,2,6,16,14,18,8,12,4]),
            'Lake Jovita - South' :
                ([4,5,4,3,4,4,3,4,5,4,5,3,5,3,4,4,4,4], [3,9,11,17,13,1,15,7,5,6,14,10,12,18,4,2,16,8]),
            'World Woods - Rolling Oaks' :
                ([4,3,5,4,5,4,4,3,4,5,4,4,3,4,4,3,4,5], [8,16,6,18,10,12,4,14,2,11,5,9,17,3,1,13,15,7]),
            'World Woods - Pine Barrens' :
                ([4,4,3,5,4,5,3,4,4,3,4,4,4,5,4,3,4,4], [16,4,18,2,8,14,12,10,6,17,15,1,7,9,13,5,11,3]),
            "Southern Hills Plantation - Morning" :
                ([4,4,3,4,5,4,5,3,4,4,4,5,3,4,4,5,3,4], [7,9,15,5,3,11,1,17,13,12,8,4,18,6,14,2,16,10]),
            'Southern Hills Plantation - Afternoon' :
                ([4,4,3,4,5,4,5,3,4,4,4,5,3,4,4,5,3,4], [7,9,15,5,3,11,1,17,13,12,8,4,18,6,14,2,16,10])
            }


    def add_player(self, name, hdcp, skins=True):
        golfer = Player(name, hdcp, self.courses, skins)
        golfer_pkl = pickle.dumps(golfer)
        self.coll.update_one({'name': name}, {'$set': {'name': name, 'player': golfer_pkl, 'skins': skins, 'hdcp': hdcp}}, upsert=True)


    def add_score(self, player, course, hole, score):
        doc = self.coll.find_one({'name': player})
        golfer = pickle.loads(doc['player'])
        hdcp = self.calc_handicap(player, course)
        # print('{}, {}, {}, {}, {}'.format(player, course, hdcp, hole, score))
        golfer.post_score(course, hole, score, hdcp)

        golfer_pkl = pickle.dumps(golfer)
        self.coll.update_one({'name': player}, {'$set': {'player': golfer_pkl}})


    def show_player_course_score(self, player, course, net=False):
        doc = self.coll.find_one({'name': player})
        golfer = pickle.loads(doc['player'])
        score = golfer.calc_course_score(course, net)
        return score


    def show_player_total_score(self, player, net=False):
        doc = self.coll.find_one({'name': player})
        golfer = pickle.loads(doc['player'])
        total_score = golfer.calc_total_score(net)
        return total_score


    def leaderboard(self, net=True):
        names = []
        players = []
        docs = self.coll.find()
        for doc in docs:
            names.append(doc['name'])
            players.append(pickle.loads(doc['player']))

        scores = []
        for player in players:
            total = 0
            for course in player.scores.keys():
                if player.calc_course_score(course, net) > 0:
                    total += player.calc_course_score(course, net)
            scores.append(total)

        rank = list(rankdata(scores, method='min'))
        # rank = list(np.unique(scores, return_inverse=True)[1])
        results = list(zip(rank, names, scores))
        sorted_results = sorted(results, key=lambda x: x[0])

        df = pd.DataFrame(sorted_results, columns=['Position', 'Name', 'Net Total'])
        # df.set_index('Position', inplace=True)

        return df


    def calc_skins(self, course, net=True):
        names = []
        players = []
        docs = self.coll.find()
        for doc in docs:
            if doc['skins'] == True:
                names.append(doc['name'])
                players.append(pickle.loads(doc['player']))

        pot = len(names) * 5
        cols = [str(x) for x in range(1, 19)]

        scores = []
        if net:
            for player in players:
                scores.append(list(player.net_scores[course].values()))
        else:
            for player in players:
                scores.append(list(player.scores[course].values()))

        df = pd.DataFrame(data=scores, index=names, columns=cols)
        low_scores = df.min(axis=0)
        # skins = []
        skins_dct = defaultdict(list)
        for hole, low_score in zip(range(1, 19), low_scores):
            if low_score == 0:
                continue
            scores = list(df[str(hole)].values)
            if scores.count(low_score) == 1:
                # skins.append((hole, df[str(hole)].idxmin()))
                skins_dct[df[str(hole)].idxmin()].append(str(hole))

        results = []
        for name in names:
            results.append((name, skins_dct[name], len(skins_dct[name])))
            # results.append((name, skins.count(name)))

        results = [(name, ', '.join(holes), n_skins) for name, holes, n_skins in results]
        sorted_results = sorted(results, key=lambda x: x[2], reverse=True)

        total_skins = sum(n for _, _, n in sorted_results)
        skin_value = pot / total_skins

        final_results = [(name, holes, skins * skin_value) for name, holes, skins in sorted_results]

        df_results = [(name, holes, int(winnings/skin_value), float(winnings)) for name, holes, winnings in final_results]

        df_skins = pd.DataFrame(df_results, columns=['Player', 'Holes Won', 'Skins', 'Winnings'])
        df_skins['Winnings'] = df_skins['Winnings'].map('${:,.2f}'.format)

        return df_skins


    def calc_teams(self, teams, course):
        # pot = len(teams) * 20
        team_scores = []
        for (p1, p2) in teams:
            doc1 = self.coll.find_one({'name': p1})
            doc2 = self.coll.find_one({'name': p2})
            g1 = pickle.loads(doc1['player'])
            g2 = pickle.loads(doc2['player'])
            s1 = g1.calc_course_score(course, net=True)
            s2 = g2.calc_course_score(course, net=True)
            team_score = s1 + s2
            team_scores.append(team_score)

        team_nums = [idx+1 for idx, _ in enumerate(range(len(teams)))]
        rank = list(rankdata(team_scores, method='min'))
        results = list(zip(rank, team_nums, team_scores))
        sorted_results = sorted(results, key=lambda x: x[0])

        clean_teams = [p1 + ' / ' + p2 for p1, p2 in teams]
        final_results = [(r, clean_teams[i-1], s) for r,i,s in sorted_results]

        df = pd.DataFrame(final_results, columns=['Position', 'Team', 'Score'])
        df['Winnings'] = 0

        first = [t for r,t,s in final_results if r == 1]
        second = [t for r,t,s in final_results if r == 2]
        third = [t for r,t,s in final_results if r == 3]

        if len(first) == 1 and len(second) == 1:
            f_winnings = 60
            s_winnings = 40
            t_winnings = 20 / len(third)
            df['Winnings'] = np.where(df['Position'] == 1, f_winnings, df['Winnings'])
            df['Winnings'] = np.where(df['Position'] == 2, s_winnings, df['Winnings'])
            df['Winnings'] = np.where(df['Position'] == 3, t_winnings, df['Winnings'])
        elif len(first) == 2:
            f_winnings = (60 + 40) / 2
            s_winnings = 20 / len(third)
            df['Winnings'] = np.where(df['Position'] == 1, f_winnings, df['Winnings'])
            df['Winnings'] = np.where(df['Position'] == 3, s_winnings, df['Winnings'])
        elif len(first) == 1  and len(second) > 1:
            f_winnings = 60
            s_winnings = (40 + 20) / len(second)
            df['Winnings'] = np.where(df['Position'] == 1, f_winnings, df['Winnings'])
            df['Winnings'] = np.where(df['Position'] == 2, s_winnings, df['Winnings'])
        elif len(first) > 2:
            f_winnings = (60 + 40 + 20) / len(first)
            df['Winnings'] = np.where(df['Position'] == 1, f_winnings, df['Winnings'])

        df['Winnings'] = df['Winnings'].map('${:,.2f}'.format)

        return df


    def player_scorecards(self, players, course):
        course_par, course_hdcps = self.courses[course]
        front_par = sum(course_par[:9])
        back_par = sum(course_par[9:])
        total_par = sum(course_par)
        par = course_par[:9] + [front_par] + course_par[9:] + [back_par, total_par, 0, 0]
        hdcp = course_hdcps[:9] + [0] + course_hdcps[9:] + [0,0,0,0]
        scores = [par, hdcp]

        for player in players:
            doc = self.coll.find_one({'name': player})
            golfer = pickle.loads(doc['player'])

            front = golfer.front_nine(course)
            front_tot = sum(front)
            back = golfer.back_nine(course)
            back_tot = sum(back)
            total = golfer.calc_course_score(course)
            net_total = golfer.calc_course_score(course, net=True)
            # hdcp = self.calc_handicap(player, course)

            score = front + [front_tot] + back + [back_tot, total, total - net_total, net_total]
            scores.append(score)

        idx = ['Par', 'Hdcp'] + players.copy()

        cols = [str(x) for x in range(1, 19)]
        all_cols = cols[:9] + ['Front'] + cols[9:] + ['Back', 'Total', 'Hdcp', 'Net']

        df = pd.DataFrame(data=scores, index=idx, columns=all_cols)
        for col in df.columns:
            df[col] = df[col].astype(str)
        df.loc['Par'] = df.loc['Par'].replace(['0'],'')
        df.loc['Hdcp'] = df.loc['Hdcp'].replace(['0'],'')
        return df


    def calc_handicap(self, player, course):
        doc = self.coll.find_one({'name': player})
        golfer = pickle.loads(doc['player'])

        if course == 'World Woods - Rolling Oaks':
            check_a = []
            check_b = []
            for c in ['Lake Jovita - North', 'Lake Jovita - South']:
                if all(golfer.show_scorecard(c).values()):
                    c_par, _ = self.courses[c]
                    check_a.append((sum(c_par) + golfer.hdcp) - golfer.calc_course_score(c) >= 4)
                    check_b.append(golfer.calc_course_score(c) - (sum(c_par) + golfer.hdcp) >= 8)
                else:
                    return golfer.hdcp

            if sum(check_a) == 2:
                return golfer.hdcp - 2
            elif sum(check_b) == 2:
                return golfer.hdcp + 2
            else:
                return golfer.hdcp

        elif course == 'World Woods - Pine Barrens':
            check1_a = []
            check1_b = []
            for c in ['Lake Jovita - North', 'Lake Jovita - South']:
                if all(golfer.show_scorecard(c).values()):
                    c_par, _ = self.courses[c]
                    check1_a.append((sum(c_par) + golfer.hdcp) - golfer.calc_course_score(c) >= 4)
                    check1_b.append(golfer.calc_course_score(c) - (sum(c_par) + golfer.hdcp) >= 8)
                else:
                    return golfer.hdcp

            if sum(check1_a) == 2:
                hdcp1 = golfer.hdcp - 2
            elif sum(check1_b) == 2:
                hdcp1 = golfer.hdcp + 2
            else:
                hdcp1 = golfer.hdcp

            check2_a = []
            check2_b = []
            for c in ['Lake Jovita - South', 'World Woods - Rolling Oaks']:
                if all(golfer.show_scorecard(c).values()):
                    c_par, _ = self.courses[c]
                    check2_a.append((sum(c_par) + hdcp1) - golfer.calc_course_score(c) >= 4)
                    check2_b.append(golfer.calc_course_score(c) - (sum(c_par) + hdcp1) >= 8)
                else:
                    return hdcp1

            if sum(check2_a) == 2:
                return hdcp1 - 2
            elif sum(check2_b) ==2:
                return hdcp1 + 2
            else:
                return hdcp1

        elif course == 'Southern Hills Plantation - Morning':
            check1_a = []
            check1_b = []
            for c in ['Lake Jovita - North', 'Lake Jovita - South']:
                if all(golfer.show_scorecard(c).values()):
                    c_par, _ = self.courses[c]
                    check1_a.append((sum(c_par) + golfer.hdcp) - golfer.calc_course_score(c) >= 4)
                    check1_b.append(golfer.calc_course_score(c) - (sum(c_par) + golfer.hdcp) >= 8)
                else:
                    return golfer.hdcp

            if sum(check1_a) == 2:
                hdcp1 = golfer.hdcp - 2
            elif sum(check1_b) == 2:
                hdcp1 = golfer.hdcp + 2
            else:
                hdcp1 = golfer.hdcp

            check2_a = []
            check2_b = []
            for c in ['Lake Jovita - South', 'World Woods - Rolling Oaks']:
                # pdb.set_trace()
                if all(golfer.show_scorecard(c).values()):
                    c_par, _ = self.courses[c]
                    check2_a.append((sum(c_par) + hdcp1) - golfer.calc_course_score(c) >= 4)
                    check2_b.append(golfer.calc_course_score(c) - (sum(c_par) + hdcp1) >= 8)
                else:
                    return hdcp1

            if sum(check2_a) == 2:
                hdcp2 = hdcp1 - 2
            elif sum(check2_b) == 2:
                hdcp2 = hdcp1 + 2
            else:
                hdcp2 = hdcp1

            check3_a = []
            check3_b = []
            for c in ['World Woods - Rolling Oaks', 'World Woods - Pine Barrens']:
                if all(golfer.show_scorecard(c).values()):
                    c_par, _ = self.courses[c]
                    check3_a.append((sum(c_par) + hdcp2) - golfer.calc_course_score(c) >= 4)
                    check3_b.append(golfer.calc_course_score(c) - (sum(c_par) + hdcp2) >= 8)
                else:
                    return hdcp2

            if sum(check3_a) == 2:
                return hdcp2 - 2
            elif sum(check3_b) == 2:
                return hdcp2 + 2
            else:
                return hdcp2

        elif course == 'Southern Hills Plantation - Afternoon':
            check1_a = []
            check1_b = []
            for c in ['Lake Jovita - North', 'Lake Jovita - South']:
                if all(golfer.show_scorecard(c).values()):
                    c_par, _ = self.courses[c]
                    check1_a.append((sum(c_par) + golfer.hdcp) - golfer.calc_course_score(c) >= 4)
                    check1_b.append(golfer.calc_course_score(c) - (sum(c_par) + golfer.hdcp) >= 8)
                else:
                    return golfer.hdcp

            if sum(check1_a) == 2:
                hdcp1 = golfer.hdcp - 2
            elif sum(check1_b) == 2:
                hdcp1 = golfer.hdcp + 2
            else:
                hdcp1 = golfer.hdcp

            check2_a = []
            check2_b = []
            for c in ['Lake Jovita - South', 'World Woods - Rolling Oaks']:
                if all(golfer.show_scorecard(c).values()):
                    c_par, _ = self.courses[c]
                    check2_a.append((sum(c_par) + hdcp1) - golfer.calc_course_score(c) >= 4)
                    check2_b.append(golfer.calc_course_score(c) - (sum(c_par) + hdcp1) >= 8)
                else:
                    return hdcp1

            if sum(check2_a) == 2:
                hdcp2 = hdcp1 - 2
            elif sum(check2_b) == 2:
                hdcp2 = hdcp1 + 2
            else:
                hdcp2 = hdcp1

            check3_a = []
            check3_b = []
            for c in ['World Woods - Rolling Oaks', 'World Woods - Pine Barrens']:
                if all(golfer.show_scorecard(c).values()):
                    c_par, _ = self.courses[c]
                    check3_a.append((sum(c_par) + hdcp2) - golfer.calc_course_score(c) >= 4)
                    check3_b.append(golfer.calc_course_score(c) - (sum(c_par) + hdcp2) >= 8)
                else:
                    return hdcp2

            if sum(check3_a) == 2:
                hdcp3 = hdcp2 - 2
            elif sum(check3_b) == 2:
                hdcp3 = hdcp2 + 2
            else:
                hdcp3 = hdcp2

            check4_a = []
            check4_b = []
            for c in ['World Woods - Pine Barren', 'Southern Hills Plantation - Morning']:
                if all(golfer.show_scorecard(c).values()):
                    c_par, _ = self.courses[c]
                    check4_a.append((sum(c_par) + hdcp3) - golfer.calc_course_score(c) >= 4)
                    check4_b.append(golfer.calc_course_score(c) - (sum(c_par) + hdcp3) >= 8)
                else:
                    return hdcp3

            if sum(check4_a) == 2:
                return hdcp3 - 2
            elif sum(check4_b) == 2:
                return hdcp3 + 2
            else:
                return hdcp3

        else:
            return golfer.hdcp


    def show_handicaps(self, course):
        names = []
        # golfers = []
        docs = self.coll.find()
        for doc in docs:
            names.append(doc['name'])
            # golfers.append(pickle.loads(doc['player']))

        hdcps = [self.calc_handicap(name, course) for name in names]
        results = list(zip(names, hdcps))
        sorted_results = sorted(results, key=lambda x: x[0])

        df_hdcps = pd.DataFrame(sorted_results, columns=['Player', 'Handicap'])

        return df_hdcps


if __name__ == '__main__':
    # past_locations_map()
    golf = PlayGolf('2020')

    print('Adding players...')
    golf.add_player('Stuart', 2, True)
    golf.add_player('Alex', 1, True)
    golf.add_player('Jerry', 5, True)
    golf.add_player('Reggie', 5, True)

    print("Adding Stuart's scores...")
    for idx, _ in enumerate(range(18)):
        golf.add_score('Stuart', 'Lake Jovita - North', idx+1, np.random.randint(3,7))
    for idx, _ in enumerate(range(18)):
        golf.add_score('Stuart', 'Lake Jovita - South', idx+1, np.random.randint(3,7))
    # for idx, _ in enumerate(range(18)):
    #     golf.add_score('Stuart', 'World Woods - Rolling Oaks', idx+1, np.random.randint(3,7))
    # for idx, _ in enumerate(range(18)):
    #     golf.add_score('Stuart', 'World Woods - Pine Barrens', idx+1, np.random.randint(3,7))
    # for idx, _ in enumerate(range(18)):
    #     golf.add_score('Stuart', 'Southern Hills Plantation - Morning', idx+1, np.random.randint(3,7))
    # for idx, _ in enumerate(range(18)):
    #     golf.add_score('Stuart', 'Southern Hills Plantation - Afternoon', idx+1, np.random.randint(3,7))

    print("Adding Alex's scores...")
    for idx, _ in enumerate(range(18)):
        golf.add_score('Alex', 'Lake Jovita - North', idx+1, np.random.randint(3,6))
    for idx, _ in enumerate(range(18)):
        golf.add_score('Alex', 'Lake Jovita - South', idx+1, np.random.randint(3,6))

    print("Adding Jerry's scores...")
    for idx, _ in enumerate(range(18)):
        golf.add_score('Jerry', 'Lake Jovita - North', idx+1, np.random.randint(3,7))
    for idx, _ in enumerate(range(18)):
        golf.add_score('Jerry', 'Lake Jovita - South', idx+1, np.random.randint(3,7))

    print("Adding Reggie's scores...")
    for idx, _ in enumerate(range(18)):
        golf.add_score('Reggie', 'Lake Jovita - North', idx+1, np.random.randint(3,7))
    for idx, _ in enumerate(range(18)):
        golf.add_score('Reggie', 'Lake Jovita - South', idx+1, np.random.randint(3,7))

    # hdcp = golf.calc_handicap('Alex', 'World Woods - Rolling Oaks')
    # df = golf.show_handicaps('World Woods - Rolling Oaks')
    # df = golf.calc_skins('Lake Jovita - South')
    #
    # teams = [('Stuart', 'Jerry'), ('Alex', 'Reggie')]
    # df = golf.calc_teams(teams, 'Lake Jovita - South')
    #
    # df2 = golf.player_scorecards(['Alex', 'Stuart'],'Lake Jovita - North')
