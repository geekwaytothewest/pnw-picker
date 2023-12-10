from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta, date
from copy import copy
import logging
import json
import csv
import labels
from reportlab.graphics import shapes
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib import colors

logger = logging.getLogger(__name__)

class CustomJSONEncoder(json.JSONEncoder):
    """A handy function to create custom JSON output. Still needed?"""
    def default(self, obj):
        if hasattr(obj, '__json__'):
            return obj.__json__()
        return json.JSONEncoder.default(self, obj)

class Game(object):
    """A game potentially has many copies."""
    def __init__(self, game_id, game_name, copies=None):
        """Input: game_id (int), game_name (string), and copies (list of Copy objects, optional)."""
        self.game_id = game_id
        self.game_name = game_name
        self.copies = copies if copies is not None else list()

    def num_copies(self):
        return len(self.copies)

    def copy_ids(self):
        return [c.copy_id for c in self.copies]

    def tsv_copies(self):
        return [[self.game_name,*c.tsv_row()] for c in self.copies]

class Copy(object):
    """A copy of a game, whether it is awardable as a prize, and who wins it."""
    def __init__(self, game_id, copy_id, allow_winning):
        """Input: game_id (int), copy_id (string), and allow_winning (bool)."""
        self.game_id = game_id
        self.copy_id = copy_id
        self.allow_winning = allow_winning
        self.winner = None

    def tsv_row(self):
        return [self.game_id, self.copy_id, self.allow_winning, self.winner]


class GameCheckout(object):
    """A single play of a game, containing players of that play.
        Contains:
            - checkout_id: an integer ID, unique per checkout
            - time_out and time_in: GMT-5 (Central) times
            - duration: the amount of time checked out for this checkout
            - game.game_id and game.game_name: ID should be exactly the same as library/P&W ID, and name is used for convenience
            - players: a list of Player objects

    """
    def __init__(self, play_json=None):
        """Input: play_json should have five keys at minimum: CheckoutID, GameID, GaneName, Checkout, and Players.

            No assumptions are made about whether the game is in the library or not. Filtering should be done before or after.

            For now, all players are kept.
        """
        if play_json is not None:
            # CheckOut info
            self.checkout_id = int(play_json['CheckoutID'])
            self.game=Game(game_id=play_json['GameID'],game_name=play_json['GameName'])

            # times and duration
            try:
                time_out = play_json['Checkout']['TimeOut'].split('.')[0]  # down to the second
                time_in = play_json['Checkout']['TimeIn'].split('.')[0]  # down to the second
            except AttributeError as err: # sometimes time_in == null and I don't know why
                time_in = time_out

            # transform times to Central (GMT-5), calculate duration
            self.time_out = datetime.fromisoformat(time_out)-timedelta(hours=5)
            self.time_in = datetime.fromisoformat(time_in)-timedelta(hours=5)
            self.duration = (self.time_in-self.time_out).total_seconds()

            # EXCEPTION DUE TO SERVER DOWNTIME ON FIRST DAY OF GEEKWAY 2023
            # bad_date = date(2023,5,18)
            # logger.info("Checkout ID {self.checkout_id} on date {self.time_out.day}")
            # if self.time_out.day == bad_date:
            #     logger.info("Checkout ID {self.checkout_id} was checked out {self.time_out}, setting to 5 second duration.")
            #     self.duration = datetime.second(5)

            # players (keep them all for now)
            self.players = [Player(
                                player_id=str(p['ID']), player_name=p['Name'],
                                wants_to_win=bool(p['WantsToWin']), rating=p['Rating'])
                            for p in play_json['Players']]

    def tsv_rows(self):
        """ Return N rows suitable for TSV output, N=#players. """
        output_rows = list()
        for p in self.players:
            output_rows.append([self.checkout_id,self.game.game_name, self.game.game_id, p.player_name, p.player_id,
                                p.wants_to_win, p.rating, self.time_out, self.time_in, self.duration/60.0])
        return output_rows

class Player(object):
    """A single player of a single play of a game (non-unique)."""

    def __init__(self, player_id=None, player_name=None, wants_to_win=True, rating=None):
        self.player_id = str(player_id)
        self.player_name = player_name
        self.wants_to_win = wants_to_win
        self.rating=rating

    def __eq__(self,other):
        """Returns true if the IDs are the same. Beware of string comparison of ints."""
        return self.player_id==other.player_id

    def __neq__(self,other):
        """Returns false if the IDs are the same. Beware of string comparison of ints."""
        return self.player_id!=other.player_id

    def __str__(self):
        return f"{self.player_id}, {self.player_name}"

    def __hash__(self):
        return hash(self.player_id)

class Win(object):
    """A single win, containing info about the game, the player, and the play."""

    _header_row = ['Game_ID','Game_Name','Copy_ID','Winner_Name','Last_Name','Winner_ID','N_plays',"Notes"]

    def __init__(self,game,copy_id,player,play,n_plays=0,notes=None):
        self.game=game
        self.copy_id=copy_id
        self.player=player
        self.play=play
        self.n_plays=n_plays
        self.notes='' if notes is None else notes
        self.last_name = self.player.player_name.split(" ")[-1]

    def list_output(self):
        """Use this for writing to TSV."""
        return [self.game.game_id, self.game.game_name, self.copy_id,
                self.player.player_name, self.last_name, self.player.player_id, self.n_plays,
                self.notes]

    def label_output(self):
        """Use this for writing to a label. [0] is the person, [1] is the game."""
        return ("{player_name} ({player_id})".format(**vars(self.player)),
                "{game.game_name} ({copy_id})".format(**vars(self)))

    def header_row():
        """Use this for the header row of the TSV."""
        return Win._header_row

def parse_games_json(filename):
    """Deserialize a list of game copies input from JSON.
        If json_str is specified, parse the string, otherwise use the file

        JSON FORMAT:
            api/games
            - ID: Game's ID, integer, one per game title
            - Name: Game's title
            - Copies: []
                per Copy:
                - ID: The string ID used in the copy barcode (AKA: LibraryID)
                - Copies.Winnable: false if it's a library copy (even if it's in the P&W collection)

                The following is not used:
                - Copies.IsCheckedOut: Boolean - Whether the copy is currently checked out or not
                - Copies.Title: redundant
                - Collection: Allows games to be moved from Library to Play and Win
                    - AllowWinning: true if the whole collection is meant to be winnable
                - Copies.CurrentCheckout: A Checkout object if the copy is checked out, else null
                - Copies.Collection.ID and Collection.Name and Collection.Color
                - Copies.Game:
                    ID: Game's ID
                    Name: Game's title
                    Copies: always null from this endpoint

        RETURNS:
            A list of all games as Game objects, each with one or more game copies.
    """

    with open(filename,'r',newline='') as f:
        m = json.load(f)

    m = m['Result']

    all_games = list()
    for g in m['Games']:
        game_id = int(g['ID'])
        copies = list()

        for c in g['Copies']:
            winnable = bool(c['Winnable'])
            copies.append(Copy(game_id=game_id, copy_id=str(c['ID']), allow_winning=winnable))

        all_games.append(Game(game_id=game_id, game_name=g['Name'], copies=copies))

    return all_games

def filter_library_games(all_games):
    """GIVEN a list of Game objects, Return a list of Game objects that only have winnable Copy objects.
        If a game has winnable and non-winnable copies, the returned list will only have the winnable copies.
        If a game has only non-winnable copies, it will not be present in the returned list.
    """
    winnable_games = list()

    for g in all_games:
        winnable_copies = [c for c in g.copies if c.allow_winning==True]
        if len(winnable_copies)>0:
            winnable_games.append(Game(game_id=g.game_id,game_name=g.game_name, copies=winnable_copies))

    return winnable_games

def parse_plays_json(filename):
    """Deserialize a list of Checkouts input from JSON.
        JSON FORMAT:
            api/plays
        USED:
            - ID: the play's ID
            - CheckoutID: the checkout's ID
            - GameID: the ID of the Game that was played (This is NOT the individual copy ID)
            - GameName: the name of the Game that was played
            - Players: []
                Player
                - ID: Badge ID of the attendee who played this game
                - Name: Name of the attendee who played this game
                - WantsToWin: Whether they want to be eligible to win this at P&W
                - Rating: parsed but not currently used

        RETURNS:
            A list of all plays as GameCheckout objects.
    """
    with open(filename,'r',newline='') as f:
        m = json.load(f)

    m = m['Result']
    all_plays = [GameCheckout(play_json=play) for play in m['Plays']]
    return all_plays

def filter_plays(all_plays, awardable_games_by_ID, min_duration=None, max_duration=None):
    """Given a list of plays and an OrderedDict of awardable games by ID, remove:
        - any plays of games not awardable
        - any play durations outside of the min and max
        - any players who do not want to win that game copy
        - any plays of games with no players

        RETURNS:
            A defaultdict of GameCheckout objects, keyed by game ID, and a defaultdict of removed plays, keyed by reason
    """
    filtered_plays = defaultdict(list)
    removed_plays = defaultdict(list)
    num_not_want_to_win = 0

    for p in all_plays:
        if p.game.game_id not in awardable_games_by_ID:
            removed_plays['not_awardable'].append(p)
        elif len(p.players)==0:
            removed_plays['no_players'].append(p)
        elif (min_duration is not None) and p.duration < min_duration:
            removed_plays['min_duration'].append(p)
        elif (max_duration is not None) and p.duration > max_duration:
            removed_plays['max_duration'].append(p)
        else:
            filtered_players = [player for player in p.players if player.wants_to_win==True]
            if len(filtered_players)==0:
                removed_plays['no_motivated_players'].append(p)
            else:
                num_not_want_to_win += (len(p.players) - len(filtered_players))
                filtered_play = copy(p)
                filtered_play.players = filtered_players
                filtered_plays[p.game.game_id].append(filtered_play)

    return filtered_plays, removed_plays

def parse_ineligible_players(ineligible_players_fn):
    """Parse a tsv file with a list of players who cannot participate in the prize drawing.

    Format is tsv-separated (ID,Player Name). If no player name is present (blank badges) that's OK.
    """
    ineligible_players=list()
    with open(ineligible_players_fn) as f:
        r = csv.reader(f, delimiter='\t')
        for row in r:
            ineligible_players.append(Player(player_id=row[0].strip(),player_name=row[1].strip()))

    logger.info(f"Found {len(ineligible_players)} ineligible players in file {ineligible_players_fn}")
    # logger.debug(json.dumps(ineligible_players,cls=CustomJSONEncoder))
    return ineligible_players

def output_winners(wins,out_fn):
    """TSV output of winners to the specified file.
        ARGUMENTS:
            wins - a list of Game objects, each with a list of Players who won
            out_fn - the TSV file
    """
    with open(out_fn,'w',newline='', encoding="utf-8") as f:
        writer = csv.writer(f,delimiter='\t')
        writer.writerow(Win._header_row)
        for w in wins:
            try:
                writer.writerow(w.list_output())
            except UnicodeEncodeError as err:
                logger.warning(f"Exception {err} when giving away {w.game.game_name} ({w.copy_id}), check results...")
                writer.writerow(w.list_output().encode('ascii', 'ignore').decode('ascii'))


def output_winners_labels(wins,out_fn):
    """label-formatted output of winners to the specified file.
        ARGUMENTS:
            wins - a list of Game objects, each with a list of Players who won
            out_fn - the labels file
    """
    # This uses Avery 6460 labels on 8.5"x11" (216mm x 279mm) sheets, with 3 columns of labels.
    # Each label is 1"x2-5/8" (25.4mm x 66.675mm) with a 2mm rounded corner. The margins are
    # automatically calculated.
    pw = 216   # actually 215.9
    ph = 279   # actually 279.4
    corner = 2
    side_margins = 5    #actually 4.76
    front_margins = 13 #actually 12.70
    lw = 66     # actually 66.675
    lh = 25     # actually 25.4
    rows = 10
    cols = 3
    specs = labels.Specification(pw, ph, cols, rows, lw, lh, corner_radius=corner,
        left_margin=side_margins, right_margin=side_margins, top_margin=front_margins,
        bottom_margin=front_margins)

    # Measure the width of the name and shrink the font size until it fits.
    def autosize_text(text, font, area_width, start_size):
        """ Shrink text to fit into the given area. Returns the appropriate font size."""
        font_size = start_size
        text_width = stringWidth(text, font, font_size)
        while text_width > area_width:
            font_size *= 0.8
            text_width = stringWidth(text, font, font_size)
        return font_size

    # Create a function to draw each label. This will be given the ReportLab drawing
    # object to draw on, the dimensions (NB. these will be in points, the unit
    # ReportLab uses) of the label, and the object to render.

    def draw_label(label, width, height, text):
        """ Expects a tuple: first entry is the winner, second is the game."""
        font = "Helvetica"
        lr_margins = 5
        padded_width = width-(lr_margins*2)
        winner_size = autosize_text(text[0],font,padded_width,14)
        game_size = autosize_text(text[1],font,padded_width,winner_size)
        winner_pos = height/2 + 5
        game_pos =  height/2 - 5 - game_size

        # Winner on top line, in blue
        label.add(shapes.String(lr_margins, winner_pos, text[0], fontName=font,
            fillColor=colors.blue, fontSize=winner_size))

        # Game on bottom line, never bigger than winner.
        label.add(shapes.String(lr_margins, game_pos, text[1], fontName=font,
            fontSize=game_size))

    # Create the sheet
    sheet = labels.Sheet(specs, draw_label, border=False)

    # Add the winners
    sheet.add_labels([w.label_output() for w in wins])

    # Save the file and we are done.
    sheet.save(out_fn)
    logger.info("{0:d} label(s) output on {1:d} page(s).".format(sheet.label_count, sheet.page_count))

def output_problem_file(problem_fn, problem_plays):
    """Output a TSV file of all plays for all games that have unawarded copies or other problems."""

    headers = ['CheckoutID','GameName','GameID','PlayerName','PlayerID','WantsToWin','Rating','TimeOut','TimeIn','Duration(min)']
    tsv_rows = list()
    for play in problem_plays:
            tsv_rows.extend(play.tsv_rows())

    with open(problem_fn,'w',newline='') as f:
        writer = csv.writer(f,delimiter='\t')
        writer.writerow(headers)
        writer.writerows(tsv_rows)

def setup_logger(app_name):
    """Creates debug and warning files based on the input app_name, in the log directory.
        By default files are appended, not overwritten.
    """
    fn_debug = 'log/'+app_name+'.debug.log'
    fn_warning = 'log/'+app_name+'.warning.log'

    logger = logging.getLogger(app_name)
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(fn_debug)
    fh.setLevel(logging.DEBUG)
    # create console handler which logs only errors
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create file handler which logs warning messages
    fh2 = logging.FileHandler(fn_warning)
    fh2.setLevel(logging.WARNING)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('[%(levelname)10s] :\t %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    fh2.setFormatter(formatter)
    # add the handlers to logger
    logger.addHandler(ch)
    logger.addHandler(fh)
    logger.addHandler(fh2)

    datestr = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.debug(f'------------ {datestr} : {app_name} : DEBUG ------------')
    logger.info(f'------------ {datestr} : {app_name} : INFO ------------')
    logger.warning(f'------------ {datestr} : {app_name} : WARNINGS ------------')

    return logger