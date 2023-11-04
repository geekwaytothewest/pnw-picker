import unittest
import random 
import pnw_picker as pnw
import csv
import sys
import urllib
import json

import http.client

import requests
import requests_file

fn_games_txt = 'test/game_names_sample.txt'
fn_players_txt = 'test/player_names_fake.txt'
fn_plays_xml = 'test/plays_test.xml'
fn_games_xml = 'test/games_test.xml'
fn_plays_json = 'test/plays_test.json'
fn_games_json = 'test/games_test.json'
api_plays_json = 'http://93a186b3.ngrok.io/Api/Plays'
api_games_json = 'http://93a186b3.ngrok.io/Api/Games'
fn_ineligible_games_tsv = 'test/ineligible_games_test.tsv'
fn_ineligible_players_tsv = 'test/ineligible_players_test.tsv'
fn_final_output = 'output/test_output.tsv'
fn_labels_output = 'output/test_labels.pdf'

# Note that most of these tests are very outdated. I'm keeping them in for now as a
# reminder of things I should be testing.

class TestParsePlays(unittest.TestCase):
    def test_number_of_plays(self):
        """The test input file should have 13 Checkouts/Plays."""
        with open(fn_games_xml) as f:
            all_games = pnw.parse_games_xml(f.read())
            self.assertTrue(len(all_games)==105)

        all_games_keyed = dict((g.game_id,g) for g in all_games)

        with open(fn_plays_xml) as f:
            all_plays = pnw.parse_plays_xml(f.read(),games_dict=all_games_keyed)
        n_players = 0
        pnw.logger.debug('checkout_id\tgame_id\tplayer_name\tplayer_id')
        for play in all_plays:
            for player in play.players:
                pnw.logger.debug('\t'.join([play.checkout_id, play.game.game_id,player.player_name,player.player_id]))
                n_players += 1
        pnw.logger.debug(f"N_players={n_players}")
        self.assertTrue(len(all_plays)==13)
        self.assertTrue(n_players==50)

    def test_api_request_json(self):
        """The API now returns JSON format. Note: this is changing constantly, so may often fail for trivial reasons."""
        s = requests.session()
        foo = s.get('http://93a186b3.ngrok.io/api/Plays')
        # print(foo.text)
        # print(foo.headers.get('content-type'))
        bar = dict(foo.json())
        # print(dict(json.loads(foo.text)))
        # print(bar['Plays'])
        self.assertTrue(len(bar['Plays'])==12,f"Found {len(bar['Plays'])} Plays, but expected 11. Plays: \n{bar['Plays']}")
        # baz = urllib.request.urlopen('http://93a186b3.ngrok.io/api/Games')
        # print(baz.read())
        

    def test_file_request_json(self):
        """The API now returns JSON format, testing it when parsing file instead."""
        s = requests.session()
        s.mount('file://',requests_file.FileAdapter())
        # s.headers.update({'content-type':'application/json'})
        # s.headers.get('content-type')
        foo = s.get('file://%s'%pnw.path_to_url(fn_plays_json))
        #print(foo.text)
        bar = dict(foo.json())
        self.assertTrue(len(bar['Plays'])==5571,
            f"Found {len(bar['Plays'])} Plays, but expected 5571. Plays: \n{bar['Plays']}"
            )
        # print(foo.json())
        # bar = json.loads(foo.text)
        # print(dict(json.loads(foo.text)))
        # print(bar['Games'])

class TestParseGames(unittest.TestCase):
    def test_number_of_games_xml(self):
        """The test input file should have 105 games and N copies. If N<1, Copies is an empty list."""
        with open(fn_games_xml) as f:
            all_games = pnw.parse_games_xml(f.read())
            self.assertTrue(len(all_games)==105)
    
    def test_games_input_json(self):
        s = requests.session()
        s.mount('file://',requests_file.FileAdapter())
        # s.headers.update({'content-type':'application/json'})
        # s.headers.get('content-type')
        foo = s.get('file://%s'%pnw.path_to_url(fn_games_json))
        #print(foo.text)
        bar = dict(foo.json())
        self.assertTrue(len(bar['Games'])==99,
            f"Found {len(bar['Games'])} Games, but expected 99. Games: \n{bar['Games']}"
            )
    
class TestSelectWinners(unittest.TestCase):
    _game_library = []
    _player_list = []
    _plays_list = []

    @classmethod
    def setUpClass(cls):
        # Create a game library of games with 4 copies each.
        print("--------- TEST SETUP ---------")
        n_copies = 3
        n_games = 33
        with open(fn_games_txt) as gf:
            game_names = [line.strip() for line in gf]
        for g,game in enumerate(game_names[:n_games]):
            copy_ids = range(g*n_copies,n_copies*(g+1))
            cls._game_library.append(pnw.Game(game_name=game,game_id=g,copy_ids=copy_ids))
        print(f"parsed {len(cls._game_library)} games from {fn_games_txt}")
            
        # Get a list of players
        with open(fn_players_txt) as pf:
            player_names = [line.strip() for line in pf]
        for p,player in enumerate(player_names):
            cls._player_list.append(pnw.Player(player_id=p,player_name=player))
        print(f"parsed {len(cls._player_list)} players from {fn_players_txt}")

        # Create a bunch of plays using those games and players
        min_players = 1
        max_players = 8
        min_plays = 10
        max_plays = 100
        checkouts = 0
        for g,game in enumerate(cls._game_library):
            n_plays = random.randint(min_plays,max_plays)
            for p in range(n_plays):
                n_players = random.randint(min_players,max_players)
                players = random.sample(cls._player_list,n_players)
                play = pnw.GameCheckout(game_obj=game,checkout_id=checkouts,players=players)
                checkouts = checkouts+1
                cls._plays_list.append(play)
        print(f"Created {len(cls._plays_list)} plays, with parameters:")
        print(f"\tmin_players, max_players: {min_players}, {max_players}")
        print(f"\tmin_plays, max_plays: {min_plays}, {max_plays}")
        '''         
            pnw.logger.debug("---- Checkouts -----")
            open('checkouts.json','w').write(json.dumps(cls._plays_list,cls=pnw.CustomJSONEncoder,indent=2))
            pnw.logger.debug("---- Games ----")
            open('games.json','w').write(json.dumps(cls._game_library,cls=pnw.CustomJSONEncoder,indent=2))
        '''
        print("--------- END TEST SETUP ---------")

    def setup_the_class_only(self):
        pass

    def test_full_games_output(self):
        pnw.logger.warning(json.dumps(self._game_library,cls=pnw.CustomJSONEncoder,indent=2))

    def test_parse_ineligible_players_file(self):
        """Test file should have 20 ineligible players."""
        ineligible_players = pnw.parse_ineligible_players(fn_ineligible_players_tsv)
        self.assertTrue(len(ineligible_players)==20)

    def test_select_game_winners_one_game(self):
        """Use the sensibly-sized text files as input. I don't expect any edge cases here."""
        game = self._game_library[0]
        all_plays = self._plays_list
        pnw.logger.debug(f"selecting game winners for {game.game_name!r} (ID {game.game_id!r})...")
        winners = pnw.select_game_winners(game,all_plays,None)
        self.assertTrue(len(winners)==len(game.copy_ids))
        pnw.logger.debug(f"Winners: {[str(w) for w in winners]}")

    def test_select_game_winners_many_games(self):
        """Use the sensibly-sized text files as input. Edge cases could happen but are rare."""
        
        all_plays = self._plays_list
        all_wins = list()
        ineligible_players = list()
        for game in self._game_library[0:50]:
            winners = pnw.select_game_winners(game,all_plays,ineligible_players)
            self.assertTrue(len(winners)==len(game.copy_ids))
            all_wins.extend(winners)
        # test no duplicates
        player_wins = dict.fromkeys([p.player_id for p in self._player_list],0)
        for win in all_wins:
            k = win.player.player_id
            player_wins[k]+=1 
            self.assertLessEqual(player_wins[k],1,f"{str(win.player.player_name)} won too many games")


    def test_select_game_winners_using_xml(self):
        # Create the Game and GameCheckout objects for testing.
        all_games = list()
        all_plays = list()
        with open(fn_games_xml) as gf:
            all_games = pnw.parse_games_xml(gf.read())

        all_games_keyed = dict((g.game_id,g) for g in all_games)

        with open(fn_plays_xml) as pf:
            all_plays = pnw.parse_plays_xml(pf.read(),all_games_keyed)

        game = all_games[0]
        pnw.logger.debug(f"selecting game winners for {game.game_name} (ID {game.game_id!r})...")

        winners = pnw.select_game_winners(game,all_plays,None)


    def test_select_game_winners_too_many_ineligibles(self):
        """If a game has few plays and is selected late, too few ineligible players may remain."""
        game = self._game_library[0]
        players = self._player_list[0:5]
        ineligible_players = players[0:2]
        play = pnw.GameCheckout(game_obj=game,checkout_id=1,players=players)
        winners = pnw.select_game_winners(game,[play],ineligible_players)
        self.assertTrue(len(winners)==len(game.copy_ids),"in this edge case an ineligible player can still win")
        
    def test_output_winners(self):
        """Tests the size of the TSV output."""
        all_plays = self._plays_list
        n_games = 50
        all_wins = list()
        ineligible_players = []
        for game in self._game_library[0:n_games]:
            game_wins = pnw.select_game_winners(game,all_plays,ineligible_players)
            self.assertTrue(len(game_wins)==len(game.copy_ids))
            all_wins.extend(game_wins)
        
        print(f"We have {len(all_wins)} winners!")
        pnw.output_winners(all_wins,'test/test_output.tsv')

    def test_parse_ineligible_game_copies(self):
        """There should be 25 copies in the test."""
        ineligible_game_copies = pnw.parse_ineligible_library_copies(fn_ineligible_games_tsv, self._game_library)
        self.assertTrue(len(ineligible_game_copies)==25)

class TestMainFunction(unittest.TestCase):

    def test_main_function_local_2018(self):
        # This tests the whole kit and kaboodle, using the 2018 local file. 
        fn_plays_json = 'test/plays.2018-final.local.json'
        fn_games_json = 'test/games.2018-final.local.json'
        fn_ineligible_players_tsv = 'test/ineligible_players_geekway_2018_final.tsv'
        fn_ineligible_games_tsv = 'test/ineligible_games_geekway_2018_final.tsv'
        out_fn_prefix = 'output/pnw_test'
        pnw.pick_all_winners(geekway_library_ids_fn=fn_ineligible_games_tsv, 
                        ineligible_players_fn=fn_ineligible_players_tsv, 
                        out_fn_prefix=out_fn_prefix, 
                        suffix=None, 
                        local_source=True, 
                        all_plays_source=fn_plays_json, 
                        all_game_copies_source=fn_games_json)

    def test_main_function_local(self):
        # This tests the whole kit and kaboodle, using the 2019 schema of the 2018 local file, with WantsToWin. 
        # 116 games, 8434 plays, only players with first names starting A-E are eligible to win.
        fn_plays_json = 'test/plays.2019-mock.local.json'
        fn_games_json = 'test/games.2018-final.local.json'
        fn_ineligible_players_tsv = 'test/ineligible_players_geekway_2018_final.tsv'
        fn_ineligible_games_tsv = 'test/ineligible_games_geekway_2018_final.tsv'
        out_fn_prefix = 'output/pnw_test'
        pnw.pick_all_winners(geekway_library_ids_fn=fn_ineligible_games_tsv, 
                        ineligible_players_fn=fn_ineligible_players_tsv, 
                        out_fn_prefix=out_fn_prefix, 
                        suffix=None, 
                        local_source=True, 
                        all_plays_source=fn_plays_json, 
                        all_game_copies_source=fn_games_json)


    def test_main_function_remote(self):
        # This tests the whole kit and kaboodle, using the api.
        fn_ineligible_players_tsv = 'test/ineligible_players_geekway_2018_final.tsv'
        fn_ineligible_games_tsv = 'test/ineligible_games_geekway_2018_final.tsv'
        out_fn_prefix = 'output/pnw_test'
        pnw.pick_all_winners(geekway_library_ids_fn=fn_ineligible_games_tsv, 
                        ineligible_players_fn=fn_ineligible_players_tsv, 
                        out_fn_prefix=out_fn_prefix, 
                        suffix=None, 
                        local_source=False)


    def test_main_function_fewer_plays_local(self):
        # Tests whether the code for problem plays works, using a local file.
        fn_plays_json = 'test/api_plays_subset.json'
        fn_games_json = 'test/api_games.json'
        fn_ineligible_players_tsv = 'test/ineligible_players_geekway_2018.tsv'
        fn_ineligible_games_tsv = 'test/ineligible_games_test.tsv'
        out_fn_prefix = 'output/pnw_test_subset'
        pnw.pick_all_winners(geekway_library_ids_fn=fn_ineligible_games_tsv, 
                        ineligible_players_fn=fn_ineligible_players_tsv, 
                        out_fn_prefix=out_fn_prefix, 
                        suffix=None, 
                        local_source=True, 
                        all_plays_source=fn_plays_json, 
                        all_game_copies_source=fn_games_json)

if __name__ == '__main__':
    unittest.main()
