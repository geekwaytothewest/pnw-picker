# custom libraries
import pnw
from pnw import logger
import pnw_api


import time
import random
import requests
import csv
import argparse
import json
from gooey import Gooey
from collections import OrderedDict
from copy import copy


# import xmltodict
# import requests_file
# import pnw_api

""" 
import time
import os
import json
from collections import OrderedDict
import labels
from reportlab.graphics import shapes
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib import colors 
"""

app_name = 'pnw-picker'
logger = pnw.setup_logger(app_name)


def pick_all_winners(ineligible_players_fn, out_fn_prefix, suffix=None, 
                        local_source=False, all_plays_source=None, all_game_copies_source=None,
                        pick_method='old_school', duration_min=None, duration_max=None):
    """The master function: Given all play-and-win entries, pick and return the winners.
    Keyword arguments:
        
        Required:
        ineligible_players_fn -- TSV file containing all ineligible players (eg staff and family)
        out_fn_prefix -- output filenames will generally be out_fn.[suffix].[extension]
        
        Optional:
        suffix = use this to avoid overwriting previous files. If None, will use a timestamp.
        local_source = True if using previously-downloaded JSON source files, otherwise use api endpoints
        all_plays_source -- if local_source=True, JSON file of all game plays
        all_game_copies_source -- if local_source=True, JSON file of all game copies
        pick_method -- standard (weighted by plays) or old_school (choose play then player)
        duration_min -- minimum duration (minutes) for a play to count
        duration_max -- maximum duration (minutes) for a play to count

    Outputs:
        games.[suffix].json -- If local_source=False, list of P&W games from the API
        plays.[suffix].json -- If local_source=False, list of P&W plays from the API
        out_fn.[suffix].tsv -- TSV list of winners and the games they won, sorted by winner name
        out_fn.[suffix].pdf -- PDF of labels to stick on P&W games, sorted by game name (Avery 6460 style)
        out_fn.[suffix].unawarded.tsv -- TSV list of plays for games that could not be awarded, due to e.g. not enough eligible players

    Returns:
        A tsv list of the winner of each played copy, one copy per row.
    """
    
    # Set the suffix if not provided (accurate to second)
    if suffix is None:
        suffix = str(int(time.time()-1.5e9))

    # Parse the inputs
    all_plays_json= None
    all_game_copies_json = None
    g = requests.session()
    p = requests.session()
    if local_source is False:
        # hard code the URL for now
        # will output to files, then parse those files
        url = 'api.event.geekwaytothewest.com'
        logger.info(f"Attempting api retrieval from {url}...")
        all_game_copies_source = ".".join(['data/games',suffix,'json'])
        all_plays_source = ".".join(['data/plays',suffix,'json'])
        games = pnw_api.retrieve_data_api('games',url)
        plays = pnw_api.retrieve_data_api('plays',url)
        with open(all_game_copies_source,'w',newline='') as f:
            json.dump(games,f,indent=3)
        with open(all_plays_source,'w',newline='') as f:
            json.dump(plays,f,indent=3)
        logger.info(f"...API data output to {all_game_copies_source} and {all_plays_source}")

    # Create the list of game copies, and a dict keyed by game ID
    # Only care about the list of awardable copies
    all_game_titles = pnw.parse_games_json(all_game_copies_source)
    all_pnw_titles = pnw.filter_library_games(all_game_titles)
    num_pnw_copies = sum([g.num_copies() for g in all_pnw_titles])
    all_pnw_titles_by_id = OrderedDict([(g.game_id,g) for g in all_pnw_titles])
    logger.info(f"Parsed {len(all_game_titles)} total game titles from {all_game_copies_source}")
    logger.info(f"Awarding {len(all_pnw_titles)} game titles with {num_pnw_copies} copies")

    # DEBUG
    all_games_fn = ".".join(['log/all_games',suffix,"tsv"])
    pnw_games_fn = ".".join(['log/pnw_games',suffix,"tsv"])

    with open(all_games_fn,'w',newline='') as f:
        tsv_rows = list()
        for title in all_game_titles:
            tsv_rows.extend(title.tsv_copies())
        writer = csv.writer(f,delimiter='\t')
        try: 
            writer.writerows(tsv_rows)
        except UnicodeEncodeError as e:
            logger.error("There is some Unicode problem with one of these records, trying one at a time:")
            for row in tsv_rows:
                logger.error(row)
                writer.writerow(row)
            raise e

    with open(pnw_games_fn,'w',newline='') as f:
        tsv_rows = list()
        for title in all_pnw_titles:
            tsv_rows.extend(title.tsv_copies())
        writer = csv.writer(f,delimiter='\t')
        writer.writerows(tsv_rows)

    # Create the list of plays
    all_plays = pnw.parse_plays_json(all_plays_source)
    logger.info(f"Parsed {len(all_plays)} total plays from {all_plays_source}")

    # Only keep the plays of awardable games
    # This includes removing games with no plays, and plays outside the allowable durations 
    all_awardable_plays_by_game, removed_plays = pnw.filter_plays(all_plays, all_pnw_titles_by_id, duration_min, duration_max)
    
    # Output the awardable plays for later use
    awardable_fn = ".".join(['log/awardable',suffix,"tsv"])
    with open(awardable_fn,'w',newline='') as f:
        rows = list()
        writer = csv.writer(f,delimiter='\t')
        for game_id,awardable_plays in all_awardable_plays_by_game.items():
            rows = list()
            for play in awardable_plays:
                for row in play.tsv_rows():
                    row.append(game_id)
                    rows.append(row)
            writer.writerows(rows)

    # Output the stuff filtered, just in case
    filtered_fn = ".".join(['log/filtered',suffix,"tsv"])
    with open(filtered_fn,'w',newline='') as f:
        rows = list()
        writer = csv.writer(f,delimiter='\t')
        for reason,filtered_plays in removed_plays.items():
            rows = list()
            for play in filtered_plays:
                for row in play.tsv_rows():
                    row.append(reason)
                    rows.append(row)
            writer.writerows(rows)
        
    # Get the starting ineligible players (like staff) 
    if ineligible_players_fn is not None:
        ineligible_players = pnw.parse_ineligible_players(ineligible_players_fn)
    else:
        logger.warning("No filename provided for ineligible players, everyone starts eligible")
        ineligible_players = list()
    n_ineligible_players_initial = len(ineligible_players)

    # Begin to pick the winners: 
    all_wins = list()
    n_prizes = sum(g.num_copies() for g in all_pnw_titles_by_id.values())
    logger.info(f"Beginning P&W giveaway for {n_prizes} game copies (after removing ineligibles) using the {pick_method} method:")

    # shuffle in place so the games are given away in random order, and give them away one at a time
    awardable_game_ids = list(all_awardable_plays_by_game.keys())
    random.shuffle(awardable_game_ids)
    problem_plays = list()
    for game_id in awardable_game_ids:
            game = all_pnw_titles_by_id[game_id]
            plays = all_awardable_plays_by_game[game_id]
            winners = select_game_winners(game,plays,problem_plays,ineligible_players,method=pick_method)
            all_wins.extend(winners)
            logger.debug(f"...{len(all_wins)} games awarded so far, now {len(ineligible_players)-n_ineligible_players_initial} players removed from eligibility")

    # Test the right number of games have been given away
    logger.info(f"We have {len(all_wins)} winners!")
    if len(all_wins)!=n_prizes:
        logger.error("Something may have gone wrong, not all games have been given away:")
        logger.error(f"\t{len(all_wins)} prizes, but {n_prizes} were expected")

    # Output the winners to TSV, sorted by winner
    out_fn = ".".join([out_fn_prefix,suffix,"tsv"])
    logger.info(f"Outputting winners to file {out_fn}...")
    all_wins.sort(key=lambda x: x.player.player_name)
    pnw.output_winners(all_wins,out_fn)

    # output the winners to labels, sorted by game
    labels_fn = ".".join([out_fn_prefix,suffix,"pdf"])
    logger.info(f"Outputting winners to labels file {labels_fn}...")
    all_wins.sort(key=lambda x: x.game.game_name)
    pnw.output_winners_labels(all_wins,labels_fn)

    # output the plays for problem games, if they exist
    if len(problem_plays) > 0:
        problem_fn = ".".join([out_fn_prefix,suffix,"unawarded.tsv"])
        logger.info(f"Some problem games were detected (dagnabbit!); outputting all plays for these games to file {out_fn}...")
        pnw.output_problem_file(problem_fn,problem_plays)

    # TEMP: output all the plays to TSV:
    # output_problem_file('output/foo.tsv',all_plays)

    logger.info(f"--- Done awarding games for file stamp {suffix}! ---")

def select_game_winners(game, plays, problem_plays, ineligible_players=None, method="old_school"):
    """Select all the winners of a given game.
    
    ARGUMENTS:
        game = a Game object, which may have multiple copies
        plays = a list of GameCheckout objects (optional: can be for all plays, or just this one; it will check)
        problem_plays = a running list of plays for games that had problems with awarding
        ineligible_players = a list of (typically) previous winners, maybe staff (theoretically should be a set?)
        method = "standard" (pick N players randomly) or "old_school" (pick a play, then pick a player)
    
    RETURNS:
        a list of winners for the game object, or an empty list if it had no plays

    ASSUMPTIONS:
        Make sure you've removed ineligible game copies first! This will not check.
    """
    problem_flag = False

    # Find all the Checkouts of the game
    if ineligible_players is None: 
        ineligible_players = list()
    this_game_plays = [play for play in plays if play.game.game_id==game.game_id]
    
    # Create the list of all eligible players for all checkouts of this game
    # Eligible = not in ineligible list, and still wants to win
    this_game_players = list()
    for play in this_game_plays:
        this_game_players.extend(play.players)
    n_total_players = len(this_game_players)
    n_total_plays = len(this_game_plays)
    eligible_players = [p for p in this_game_players if (p.wants_to_win==True and p not in ineligible_players)]
    eligible_players_unique = set(eligible_players)
    logger.debug(f"Game {game.game_name}, with {game.num_copies()} copies, has {n_total_plays} plays "+
                    f"and {n_total_players} non-unique players, {len(eligible_players_unique)} unique players still eligible")
    
    winners = list()
    copies_to_award = game.copy_ids()

    # Error checking: make sure the game has copies to award
    if len(copies_to_award)==0:
        logger.warning(f"Why are you trying to award this game? Game {game.game_name}, ID {game.game_id}) had no copies to award!")
        problem_flag = True
        return list()

    # In the edge case where there are more copies than players, they should all get a copy!
    elif len(copies_to_award) >= len(eligible_players_unique):
        logger.warning(f"This is embarrassing: Game {game.game_name}, with {game.num_copies()} copies, had {len(eligible_players_unique)} eligible players, so some may go unclaimed!")
        copies_to_award = copies_to_award[:len(eligible_players_unique)]
        winners = list(eligible_players_unique)
        ineligible_players.extend(winners)
        problem_flag = True

    elif method=="standard":
        """
        Select N random winners, N = # copies
        Shuffle in-place, then iterate through the shuffled list
        Once an eligible player is found, add them to the winner list, 
        then remove them from further consideration, even if they have more plays for this game
        """
        random.shuffle(eligible_players)            # careful not to use 'unique' here: more plays means more chances
        problem_flag = True                         # set to false when exit is successful
        for player in eligible_players:
            if player not in ineligible_players:
                winners.append(player)
                ineligible_players.append(player)
            if len(winners)==len(copies_to_award):  # you've found enough, now stop
                problem_flag = False
                break    

    elif method=="old_school":
        """
        Shuffle plays in place, then iterate through the shuffled list
        Add one player per play until the correct number of copies are awarded
        problem_flag will remain True if you get through all the plays without awarding all the copies
        """
        random.shuffle(this_game_plays)
        problem_flag=True   # this will be set to False once a normal exit condition is identified
        for play in this_game_plays:
            this_play_eligible = [p for p in play.players if (p.wants_to_win==True and p not in ineligible_players)] # should filter before but just in case

            if len(this_play_eligible)>0:
                winner = random.choice(this_play_eligible)
                winners.append(winner)
                ineligible_players.append(winner)

            if len(winners)==len(copies_to_award):  # you've selected enough winners, get outta here
                problem_flag=False
                break

        # If you don't award all the copies, you might still have some eligible players who just didn't get a chance because of the picker thing
        # In that case, revert to the 'standard' method
        # Temporary location; refactor this probably so we do it only in one place
        if problem_flag==True:
            logger.warning(f"Old School method awarded only {len(winners)} of {game.num_copies()} copies of Game {game.game_name}, trying with standard method...")
            random.shuffle(eligible_players)            # careful not to use 'unique' here: more plays means more chances
            for player in eligible_players:
                if player not in ineligible_players:
                    winners.append(player)
                    ineligible_players.append(player)
                if len(winners)==len(copies_to_award):  # you've found enough, now stop
                    problem_flag = False
                    logger.warning(f"...success, the standard method rectified the Old School problem")
                    break    


    else: 
        raise NotImplementedError()

    wins=list()
    for copy_id,winner in zip(copies_to_award,winners):
        n_plays = len([p for p in this_game_players if p.player_id==winner.player_id])
        note = f"{n_total_plays} total eligible plays, {n_total_players} total motivated players"
        
        if problem_flag is True:
            note = f"CHECK UNAWARDED GAMES FILE: {len(eligible_players)} eligible players, "+note
        
        wins.append(pnw.Win(game=game, copy_id=copy_id, player=winner, play=None,
                            n_plays=n_plays,notes=note))

    # If there was a problem, put all the plays on the problem_plays list
    if problem_flag is True:
        problem_plays.extend(this_game_plays)
        logger.warning(f"Check Problem File: only {len(winners)} copies of game {game.game_name}, ID {game.game_id} awarded")

    return wins


@Gooey
def main():
    p = argparse.ArgumentParser(description='Play & Win Prize Picker')
    p.add_argument('output_fn_prefix', action="store", 
                    help="filename as prefix for final winner output")
    p.add_argument('--local', action="store_true", dest="is_local", default=False, 
                    help="(optional) if set, specifies the source as a local file, otherwise an API")
    p.add_argument('-g', '--games_source', action="store", default=None,
                    help="local json source of game names and game copy ids, if --local is set")
    p.add_argument('-p', '--plays_source', action="store", default=None,
                    help="local json source of game checkouts and players, if --local is set")
    p.add_argument('--ineligible_players_fn', action="store", default=None,
                    help="a tsv file with ID,Player Name of all ineligible players (such as staff)")
    p.add_argument('--method', action="store", choices=['standard', 'old_school'],
                    help="standard (weighted by plays) or old_school (choose play then player)")
    p.add_argument('--duration_min', action="store", default=None, type=float,
                    help="minimum duration (minutes) for a play to count")
    p.add_argument('--duration_max', action="store", default=None, type=float,
                    help="maximum duration (minutes) for a play to count")


    args = p.parse_args()

    # change duration to seconds
    if args.duration_min is not None:
        args.duration_min *= 60.0
    if args.duration_max is not None:
        args.duration_max *= 60.0

    pick_all_winners(out_fn_prefix=args.output_fn_prefix,
                    local_source=args.is_local,
                    all_plays_source=args.plays_source, 
                    all_game_copies_source=args.games_source, 
                    ineligible_players_fn=args.ineligible_players_fn,
                    pick_method = args.method,
                    duration_min = args.duration_min,
                    duration_max = args.duration_max
                    )

if __name__ == '__main__':
    main()

