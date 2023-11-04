from pnw_picker import Game,Player
import csv
import random
from collections import OrderedDict
import argparse
import json


def import_games_csv(fn_csv):
    """Returns a list of Games(). 
    Assigns ids to each game title incrementally, assuming they're spelled exactly.
    File format: GameTitle, LibraryID, OwnerName (unused).
    """
    # fieldnames= ['GameTitle','LibraryID','OwnerName'] #not sure why I can't use this
    game_names = dict()
    games = []
    with open(fn_csv) as f:
        reader = csv.DictReader(f,fieldnames=None)
        for row in reader:
            game_title=row['GameTitle']
            copy_id = row['LibraryID']
            game_names.setdefault(game_title,list()).append(copy_id)

    game_id_counter=0
    for title in game_names:
        # assign random game_ids
        game_id_counter+=1
        games.append(Game(game_id=game_id_counter,
                            game_name=title,
                            copy_ids=game_names[title]))
    
    return games

def import_players_csv(fn_csv):
    """Returns a list of Players(). 
    File format: Name, BadgeID.
    """
    fieldnames= ['Name','BadgeID']
    players = []
    with open(fn_csv) as f:
        reader = csv.DictReader(f,fieldnames)
        for row in reader:
            players.append(Player(player_id=row['BadgeID'],player_name=row['Name']))
    return players

def create_mock_plays(players, games, num_plays, min_players, max_players, seed=None):
    """Create a list of num_plays mock plays, from a list of Players() and Games()."""
    # for each play:
        # pick a game title 
        # pick a copy ID
        # pick players players
    random.seed(a=seed)
    all_plays = []
    for n in range(0,num_plays):
        p = OrderedDict()
        game = random.choice(games)
        p['play_id'] = n+1
        p['game_title'] = game.game_name
        p['game_id'] = game.game_id
        p['copy_id'] = random.choice(game.copy_ids)
        num_players = random.randint(min_players,max_players)
        p['players'] = random.sample(players,num_players)
        all_plays.append(p)
    
    return all_plays


if __name__ == '__main__':
    a = argparse.ArgumentParser(description='Play & Win Mock Plays Maker')
    a.add_argument('all_games_source', action="store", 
                    help="CSV source of game names and game copy ids")
    a.add_argument('all_players_source', action="store", 
                    help="CSV source of game checkouts and players")
    a.add_argument('output_fn', action="store", 
                    help="tsv filename for list of plays")
    a.add_argument('-r', '--readable', action="store_true",default=False,
                    help="Output in mock-entry format, otherwise straight tsv")
    a.add_argument('-n', '--num_plays', action="store",default=1000,type=int,
                    help="Number of plays, default=1000")
    a.add_argument('-j', '--json_fn', action="store",default=None,
                    help="Output to a JSON file also (add a games prefix for the game list)")

    args = a.parse_args()

    games = import_games_csv(args.all_games_source)
    players = import_players_csv(args.all_players_source)
    plays = create_mock_plays(players,games,args.num_plays,1,6)

    if args.readable==True: # output in mock-entry format (readable by people)
        with open(args.output_fn,'w',newline='') as f:
            w = csv.writer(f,dialect='excel')
            for p in plays:
                w.writerow(['PlayID','Game',p['game_title'],
                            p['copy_id'],'*'+p['copy_id']+'*',
                            'Rating'])

                num_players = len(p['players'])
                for n,player in enumerate(p['players']):
                    last_col = None
                    rating = random.choice([None,1,2,3,4,5])

                    if n==num_players-1:
                        last_col = '*'+player.player_id+'*'
                    w.writerow([p['play_id'],'Player',player.player_name,
                        player.player_id,last_col,rating])
                
                w.writerow([None]*6)

    else: # output in regular TSV format
        with open(args.output_fn,'w',newline='') as f:
            w = csv.writer(f,dialect='excel')
            w.writerow(['PlayID','Game','GameID','CopyID','Player','PlayerID','Rating'])
            for p in plays:

                num_players = len(p['players'])
                for n,player in enumerate(p['players']):
                    last_col = None
                    rating = random.choice([None,1,2,3,4,5])

                    w.writerow([p['play_id'],p['game_title'],p['game_id'],
                            p['copy_id'],player.player_name,
                            player.player_id,rating])
    
    if args.json_fn is not None:
        # first make the game list
        j = dict()
        j['Errors']=[]
        j['Result']=dict()
        j['Result']['Games'] = list()

        for g in games:
            foo = dict(ID=int(g.game_id), Name=g.game_name)
            foo['Copies'] = list()
            for c in g.copy_ids:
                bar = dict(ID=int(c), IsCheckedOut=False, CurrentCheckout=None)
                bar['Game'] = dict(ID=g.game_id,Name=g.game_name,Copies=None)
                foo['Copies'].append(bar)
            j['Result']['Games'].append(foo)
        with open(args.json_fn+'.games.json','w',newline='') as f:
            json.dump(j,f,indent=3)

        # Now make the plays json list
        j['Errors']=[]
        j['Result']=dict()
        j['Result']['Plays']=list()

        for p in plays:
            foo = dict(ID=p['play_id'],CheckoutID=p['play_id'],
                GameID=p['game_id'],GameName=p['game_title'])
            foo['Players'] = list()
            for player in p['players']:
                foo['Players'].append(dict(ID=player.player_id,Name=player.player_name))
            j['Result']['Plays'].append(foo)
        with open(args.json_fn,'w',newline='') as f:
            json.dump(j,f,indent=3)
        
        