import genanki
import json
import random
import re
import os
from bs4 import BeautifulSoup

# Complete AnKing CSS from your provided code
ANKING_CSS = """
/*    ANKINGOVERHAUL   */

/* The AnKing wishes you the best of luck! Be sure to check out our YouTube channel and Instagram
 for all things Anki and Med School related (including how to customize this card type and use these decks):  
		www.AnKingMed.com
			@ankingmed    			
*/

/*#########################################################
################  USER CUSTOMIZATION START  ##############*/
/* You can choose colors at www.htmlcolorcodes.com */

/* TIMER ON/OFF */
.timer {
  display: block;
  /* 'none' or 'block' */
}

/* TAGS ON/OFF DESKTOP & MOBILE*/
#tags-container {
  display: none;
  /* 'none' or 'block' */
}

.mobile #tags-container {
  display: none;
  /* 'none' or 'block' */
}

/* MOVE TAGS UP FOR 'NO-DISTRACTIONS' ADD-ON */
#tags-container {
  padding-bottom: 0px;
  /* 0 normal, 55 to move up */
}

/*~~~~~~~~~FONT SIZE~~~~~~~~~*/
/*NOTE: anything with 'px' will keep a font that size indefinitely, 
'rem' is a fraction of this size above and allows all text to change size with the above setting */
/* Desktop */
html {
  font-size: 28px;
}

/* Mobile */
.mobile {
  font-size: 28px;
}

/*REVEALED HINTS FONT SIZE*/
.hints {
  font-size:.85rem;
}

/*~~~~~~~~~FONT STYLE~~~~~~~~~*/
.card,
kbd {
  font-family: Arial Greek, Arial;
  /*Step exam's font is Arial Greek*/
}

/*~~~~~~~MAX IMAGE HEIGHT/WIDTH~~~~~~~*/
img {
  max-width: 85%;
  max-height: 100%;
}

/*~~~~~~~~~COLORS~~~~~~~~~/
/* Default Text Color */
.card {
  color: black;
}

/* Background Color */
.card {
  background-color: #D1CFCE;
}

/* Cloze Color */
.cloze,.cloze b,.cloze u,.cloze i {
  color: blue;
}

/* One by One Cloze Color */
.cloze.one-by-one,.cloze.one-by-one b,.cloze.one-by-one u,.cloze.one-by-one i {
  color: #009400;
}

/* One by One Cloze Hint Color */
.cloze-hint,.cloze-hint b,.cloze-hint u,.cloze-hint i {
  color: #009400;
}

/* "Extra" Field Color */
#extra, #extra i {
  color: navy;
}

/* Hint Reveal Color */
.hints {
  color: #4297F9;
}

/* Missed Questions Hint Reveal Color */
#missed {
  color: red;
}

/* Timer Countdown Color */
.timer {
  color: transparent;
}

/* Empty Link Color */
a:not([href]),
a[href^="javascript:"] {
  text-decoration: none;
  color: inherit;
}

/* Highlight Red for High-Yield */
.highlight-red {
    color: red!important; /* Ensure it's red */
}

/*~~~~~~~~NIGHT MODE COLORS~~~~~~~~*/
/* NM Default Text Color */
.nightMode.card,
.night_mode.card {
  color: #FFFAFA!important;
}

/* NM Background Color */
.nightMode.card,
.night_mode.card {
  background-color: #272828!important;
}

/* NM Cloze Color */
.nightMode.cloze,.nightMode.cloze b,.nightMode.cloze u,.nightMode.cloze i,
.night_mode.cloze,.night_mode.cloze b,.night_mode.cloze u,.night_mode.cloze i {
  color: #4297F9!important;
}

/* NM One by One Cloze Color */
.nightMode.cloze.one-by-one,.nightMode.cloze.one-by-one b,.nightMode.cloze.one-by-one u,.nightMode.cloze.one-by-one i,
.night_mode.cloze.one-by-one,.night_mode.cloze.one-by-one b,.night_mode.cloze.one-by-one u,.night_mode.cloze.one-by-one i {
    color: #009400!important;
}

/* NM One by One Cloze Hint Color */
.nightMode.cloze-hint,.nightMode.cloze-hint b,.nightMode.cloze-hint u,.nightMode.cloze-hint i,
.night_mode.cloze-hint,.night_mode.cloze-hint b,.night_mode.cloze-hint u,.night_mode.cloze-hint i {
    color: #009400!important;
}

/* NM "Extra" Field Color */
.nightMode #extra,.nightMode #extra i,
.night_mode #extra,.night_mode #extra i {
  color: magenta;
}

/* NM Hint Reveal Color */
.nightMode.hints,
.night_mode.hints {
  color: cyan;
}

/* ~~~~~COLOR ACCENTS FOR BOLD-ITALICS-UNDERLINE~~~~~~*/
b {
  color: inherit;
}

u {
  color: inherit;
}

i {
  color: inherit;
}

/*################  USER CUSTOMIZATION END  ################
###########################################################*/

/* Styling For Whole Card*/
.card {
  text-align: center;
  font-size: 1rem;
  height: 100%;
  margin: 0px 15px;
  flex-grow: 1;
  padding-bottom: 1em;
  margin-top: 15px;
}

.mobile.card {
  padding-bottom: 5em;
  margin: 1ex.3px;
}

/* Style the horizontal line */
hr {
  opacity:.7
}

/* Formatting For Timer */
.timer {
  font-size: 20px;
  margin: 12em auto auto auto;
}

/* ~~~~~~~~~ FIELDS ~~~~~~~~~ */
/* Cloze format */
.cloze {
  font-weight: bold;
}

/* Adjustments For Cloze Edit In Review On Mobile */
.clozefield,
.mobile.editcloze {
  display: none;
}

.editcloze,
.mobile.clozefield {
  display: block;
}

/* Text When Hint Is Shown*/
.hints {
  font-style: italic;
}

/*add spacing between hints and extra field*/
.hints+#extra {
  margin-top: 1rem;
}

/* Extra Field */
#extra {
  font-style: italic;
  font-size: 1rem;
}

/* ~~~~~~~~~ TAGS ~~~~~~~~~ */
/* Container To Fix Tags At Bottom Of Screen */
#tags-container {
  position: fixed;
  bottom:.5px;
  width: 100%;
  line-height:.45rem;
  margin-left: -15px;
  background-color: transparent;
}

/* Clickable Tags (need to download the add-on) */
kbd {
  display: inline-block;
  letter-spacing:.1px;
  font-weight: bold;
  font-size: 10px!important;
  text-shadow: none!important;
  padding: 0.05rem 0.1rem!important;
  margin: 1px!important;
  border-radius: 4px;
  border-width: 1.5px!important;
  border-style: solid;
  background-color: transparent!important;
  box-shadow: none!important;
  opacity: 0.5;
  vertical-align: middle!important;
  line-height: auto!important;
  height: auto!important;
}

/* Tag Becomes More Visible On Hover */
kbd:hover {
  opacity: 1;
  transition: opacity 0.2s ease;
}

/* Tag Colors */
kbd:nth-of-type(1n+0) {
  border-color: #F44336;
  color: #F44336!important;
}

kbd:nth-of-type(2n+0) {
  border-color: #9C27B0;
  color: #9C27B0!important;
}

kbd:nth-of-type(3n+0) {
  border-color: #3F51B5;
  color: #3F51B5!important;
}

kbd:nth-of-type(4n+0) {
  border-color: #03A9F4;
  color: #03A9F4!important;
}

kbd:nth-of-type(5n+0) {
  border-color: #009688;
  color: #009688!important;
}

kbd:nth-of-type(6n+0) {
  border-color: #C0CA33;
  color: #C0CA33!important;
}

kbd:nth-of-type(7n+0) {
  border-color: #FF9800;
  color: #FF9800!important;
}

kbd:nth-of-type(8n+0) {
  border-color: #FF5722;
  color: #FF5722!important;
}

kbd:nth-of-type(9n+0) {
  border-color: #9E9E9E;
  color: #9E9E9E!important;
}

kbd:nth-of-type(10n+0) {
  border-color: #607D8B;
  color: #607D8B!important;
}

/* Tag Mobile Adjustments */
.mobile kbd {
  opacity:.9;
  margin: 1px!important;
  display: inline-block;
  font-size: 10px!important;
}

.mobile #tags-container {
  line-height: 0.6rem;
  margin-left: 0px;
}

/* MNEMONICS LEFT JUSTIFIED */
.mnemonics {
  display: inline-block;
  max-width: 50%;
  text-align: left;
}

.mobile.mnemonics {
  max-width: 90%;
}

.centerbox {
  text-align: center;
}

/* LISTS */
ul, ol {
  padding-left: 40px;
  max-width: 50%;
  margin-left: auto;
  margin-right: auto;
  text-align: left;
}

ul ul, table ul, ol ol, table ol {
  padding-left: 20px;
  max-width: 100%;
  margin-left: 0;
  margin-right: 0;
  display: block;
}

.mobile ul {
  text-align: left;
  max-width: 100%;
}

.mobile ol {
  text-align: left;
  max-width: 100%;
}
"""

# Simplified AnKing JavaScript for core functionality
ANKING_JS = """
<script>
// AnKing Core JavaScript
var autoflip = false;
var minutes = 0;
var seconds = 9;
var timeOverMsg = "<span style='color:#CC5B5B'>!<br/>!<br/>!<br/>!<br/>!<br/>!</span>";

// Timer functionality
function countdown() {
    var totalSeconds = minutes * 60 + seconds;
    if (totalSeconds > 0) {
        var timer = setInterval(function() {
            if (totalSeconds <= 0) {
                clearInterval(timer);
                document.getElementById("s2").innerHTML = timeOverMsg;
            } else {
                var mins = Math.floor(totalSeconds / 60);
                var secs = totalSeconds % 60;
                document.getElementById("s2").innerHTML = mins + ":" + (secs < 10 ? "0" : "") + secs;
                totalSeconds--;
            }
        }, 1000);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    if (typeof countdown === 'function') {
        countdown();
    }
});

// Cloze one-by-one functionality (simplified)
document.addEventListener('keydown', function(event) {
    if (event.key === 'n' || event.key === 'N') {
        // Reveal next cloze logic would go here
        console.log('Reveal next cloze');
    }
});
</script>
"""

# Convert [CLOZE::text] to {{c#::text}} format
def convert_cloze_placeholder(text):
    """Convert [CLOZE::text] placeholders to Anki {{c#::text}} format"""
    if not text:
        return text
    
    # Find all [CLOZE::...] patterns
    cloze_pattern = r'\[CLOZE::([^\]]+)\]'
    matches = re.findall(cloze_pattern, text)
    
    # Replace each match with numbered cloze format
    result = text
    for i, match in enumerate(matches, 1):
        old_pattern = f'[CLOZE::{match}]'
        new_pattern = f'{{{{c{i}::{match}}}}}'
        result = result.replace(old_pattern, new_pattern, 1)
    
    return result

# Create AnKing model
def get_anking_model():
    """Create the complete AnKing model with all fields and templates"""
    
    # Consistent model IDs for proper Anki tracking
    ANKING_MODEL_ID = 1607392319
    ANKING_DECK_ID = 2059400110

    # Define all AnKing fields
    fields = [
        {'name': 'Front'},
        {'name': 'Back'}, 
        {'name': 'Extra'},
        {'name': 'Vignette'},
        {'name': 'Mnemonic'},
        {'name': 'Image'}
    ]

    # AnKing templates with full functionality
    templates = [
        {
            'name': 'AnKing Basic Card',
            'qfmt': f"""
                <div class="card-content">
                    <div id="text">{{{{Front}}}}</div>
                    <div class="timer" id="s2"></div>
                    <a href="https://www.ankingmed.com"><img src="_AnKingIcon.png" alt="The AnKing" id="pic"></a>
                </div>
                {ANKING_JS}
            """,
            'afmt': f"""
                {{{{FrontSide}}}}
                <hr id="answer">
                <div class="answer-text">{{{{Back}}}}</div>

                {{{{#Extra}}}}
                <div id="extra">{{{{Extra}}}}</div>
                {{{{/Extra}}}}

                {{{{#Vignette}}}}
                <div id="vignette-section">
                    <h3>Clinical Vignette</h3>
                    <div class="vignette-content">{{{{Vignette}}}}</div>
                </div>
                {{{{/Vignette}}}}

                {{{{#Mnemonic}}}}
                <div id="mnemonic-section">
                    <h3>Mnemonic</h3>
                    <div class="mnemonic-content">{{{{Mnemonic}}}}</div>
                </div>
                {{{{/Mnemonic}}}}

                {{{{#Image}}}}
                <div id="image-section">
                    <img src="{{{{Image}}}}" alt="Card Image">
                </div>
                {{{{/Image}}}}

                {ANKING_JS}
            """,
        },
        {
            'name': 'AnKing Cloze Card',
            'qfmt': f"""
                <div class="card-content">
                    <div id="text">{{{{cloze:Front}}}}</div>
                    <div class="timer" id="s2"></div>
                    <a href="https://www.ankingmed.com"><img src="_AnKingIcon.png" alt="The AnKing" id="pic"></a>
                </div>
                {ANKING_JS}
            """,
            'afmt': f"""
                {{{{FrontSide}}}}
                <hr id="answer">
                <div class="answer-text">{{{{cloze:Back}}}}</div>

                {{{{#Extra}}}}
                <div id="extra">{{{{Extra}}}}</div>
                {{{{/Extra}}}}

                {{{{#Vignette}}}}
                <div id="vignette-section">
                    <h3>Clinical Vignette</h3>
                    <div class="vignette-content">{{{{Vignette}}}}</div>
                </div>
                {{{{/Vignette}}}}

                {{{{#Mnemonic}}}}
                <div id="mnemonic-section">
                    <h3>Mnemonic</h3>
                    <div class="mnemonic-content">{{{{Mnemonic}}}}</div>
                </div>
                {{{{/Mnemonic}}}}

                {{{{#Image}}}}
                <div id="image-section">
                    <img src="{{{{Image}}}}" alt="Card Image">
                </div>
                {{{{/Image}}}}

                {ANKING_JS}
            """,
        }
    ]

    # Create the Anki Model
    my_model = genanki.Model(
        ANKING_MODEL_ID,
        'AnKing-Like Medical Flashcards',
        fields=fields,
        templates=templates,
        css=ANKING_CSS
    )
    return my_model, ANKING_DECK_ID

# Main function to create AnKing deck
def create_anki_deck(cards_data, output_filename="AnKing_Medical_Deck.apkg"):
    """Create AnKing-style deck from card data"""
    my_model, ANKING_DECK_ID = get_anking_model()
    my_deck = genanki.Deck(
        ANKING_DECK_ID,
        'AnKing Medical Deck'
    )

    media_files = []

    for card_info in cards_data:
        card_type = card_info.get('type', 'basic')
        front_content = card_info.get('front', card_info.get('question', ''))
        back_content = card_info.get('back', card_info.get('answer', ''))
        extra_content = card_info.get('extra', card_info.get('additional_notes', card_info.get('notes', '')))
        vignette_content = card_info.get('vignette', '')
        mnemonic_content = card_info.get('mnemonic', '')
        image_ref = card_info.get('image_ref', card_info.get('image', ''))
        tags = card_info.get('tags', [])

        # Convert [CLOZE::text] to {{c#::text}} for cloze cards
        if card_type == 'cloze':
            front_content = convert_cloze_placeholder(front_content)
            back_content = convert_cloze_placeholder(back_content)

        # Handle image embedding
        if image_ref:
            image_path = os.path.join('media', image_ref)
            if os.path.exists(image_path):
                media_files.append(image_path)

        # Create the note fields
        fields_data = [
            front_content,
            back_content,
            extra_content,
            vignette_content,
            mnemonic_content,
            image_ref
        ]

        # Handle tags - convert to list if string
        if isinstance(tags, str):
            if '::' in tags:
                tags = [tag.strip() for tag in tags.split('::') if tag.strip()]
            else:
                tags = [tag.strip() for tag in tags.split() if tag.strip()]
        elif not isinstance(tags, list):
            tags = []

        note = genanki.Note(
            model=my_model,
            fields=fields_data,
            tags=tags
        )
        
        my_deck.add_note(note)

    # Create the Anki package
    my_package = genanki.Package(my_deck)
    my_package.media_files = media_files

    # Write the package to a file
    my_package.write_to_file(output_filename)
    
    return {
        'success': True,
        'filename': output_filename,
        'card_count': len(cards_data),
        'media_count': len(media_files)
    }