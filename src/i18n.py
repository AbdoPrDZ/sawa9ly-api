"""Languages, and the words a person is actually shown.

Two things live here. `Locale` is the set of languages this installation speaks
and how each one is written; `Messages` is the catalogue of every user-facing
string, keyed by a stable name rather than by its English text.

**Why the catalogue is keyed rather than looked up by text:** the English string
is not a stable identifier. Rewording "Product 5663 is available" must not
orphan the Arabic and French versions of it, so nothing is ever found by matching
prose. A key survives a reword; a sentence does not.

**Where a language is remembered** is a per-user `Setting`, not a column, so
adding one is not a migration. `User.locale` is the only thing that reads it.

**A missing translation falls back to English rather than raising.** A language
that is one string behind is a rough edge; a notification that fails to build
because somebody added a message and forgot a language is an outage, and the
product went out of stock regardless of what the bot says. An *unknown key* is
the opposite and does raise, because that is a bug in the caller and silently
returning English would hide it.

**Numbers keep Western digits in every language.** Arabic locales may write
١٦٬٠٠٠, and this is a deliberate non-choice: the prices in these messages are
compared by eye against the site, and a reader who has to re-parse a price in
different digits before they can act on it has been slowed down by the
localisation. Only the thousands separator changes.
"""

#: The space French puts between groups of three digits.
#:
#: A no-break space, so a price cannot break across two lines in a chat bubble.
#: **Not** the narrow no-break space (U+202F) that current French typography
#: prefers: that is the right choice in a browser with a modern font and the wrong
#: one in a Telegram message, where a client without the glyph in its font shows a
#: box. A message about a price has to be readable everywhere, and U+00A0 is
#: supported everywhere.
NO_BREAK_SPACE = " "


class Locale:
  """The languages this installation speaks."""

  EN = "en"
  FR = "fr"
  AR = "ar"

  ALL = (EN, FR, AR)
  DEFAULT = EN

  #: Written right to left. The dashboard mirrors its whole layout for these.
  RTL = (AR,)

  @staticmethod
  def is_valid(value):
    return value in Locale.ALL

  @staticmethod
  def is_rtl(value):
    return value in Locale.RTL

  @staticmethod
  def of(value):
    """The named language, or the default when it is missing or unknown.

    Never raises: this runs against stored settings, and a hand-edited row
    saying `kl` is not worth refusing to render over.
    """
    return value if Locale.is_valid(value) else Locale.DEFAULT

  @staticmethod
  def numbers(value, locale=DEFAULT):
    """A price with the thousands separator this language writes.

    See the module docstring on why the digits stay Western.
    """
    if value is None:
      return ""

    grouped = f"{value:,}"

    if locale == Locale.FR:
      return grouped.replace(",", NO_BREAK_SPACE)

    return grouped


class Messages:
  """Every string a person is shown, in every language.

  One entry per key, one line per language, so a missing translation is visible
  as a short row rather than hidden somewhere. Templates use `str.format` fields;
  every caller must supply them, because a field that is not filled in is a
  sentence with a hole in it.
  """

  @staticmethod
  def get(key, locale=Locale.DEFAULT, **fields):
    """The `key` message in `locale`.

    Falls back to English for a language that is missing this particular key.
    """
    entry = Messages._entry(key)
    language = Locale.of(locale)
    template = entry.get(language) or entry[Locale.EN]

    return template.format(**fields)

  @staticmethod
  def _entry(key):
    """The translations for one key.

    Raises:
        KeyError: If no message has that name. That is a bug in the caller, and
          it must not be papered over with an English default.
    """
    try:
      return CATALOGUE[key]
    except KeyError:
      raise KeyError(
        f"No message named {key!r}. Known messages: "
        f"{', '.join(sorted(CATALOGUE))}"
      ) from None


#: key -> language -> template.
#:
#: The English is the fallback and the reference: if a phrase is unclear here it
#: will be unclear in translation too. Ordered by the flow of a notification —
#: availability, price, then the framing around them.
CATALOGUE: dict[str, dict[str, str]] = {
  # --- availability ----------------------------------------------------
  "product.available.headline": {
    Locale.EN: "Product {id} is available",
    Locale.FR: "Le produit {id} est disponible",
    Locale.AR: "المنتج {id} متوفر الآن",
  },
  "product.available.detail": {
    Locale.EN: "It was not known to be in stock before.",
    Locale.FR: "Sa disponibilité n'était pas connue auparavant.",
    Locale.AR: "لم يكن معروفًا أنه متوفر من قبل.",
  },
  "product.unavailable.headline": {
    Locale.EN: "Product {id} is no longer available",
    Locale.FR: "Le produit {id} n'est plus disponible",
    Locale.AR: "المنتج {id} لم يعد متوفرًا",
  },
  "product.unavailable.detail": {
    Locale.EN: "It has gone out of stock.",
    Locale.FR: "Il est en rupture de stock.",
    Locale.AR: "لقد نفد من المخزون.",
  },
  "product.available_again.headline": {
    Locale.EN: "Product {id} is available again",
    Locale.FR: "Le produit {id} est de nouveau disponible",
    Locale.AR: "المنتج {id} متوفر من جديد",
  },
  "product.available_again.detail": {
    Locale.EN: "It is back in stock.",
    Locale.FR: "Il est de retour en stock.",
    Locale.AR: "عاد إلى المخزون.",
  },

  # --- price -----------------------------------------------------------
  "price.dropped.headline": {
    Locale.EN: "Price dropped to {now}",
    Locale.FR: "Le prix a baissé à {now}",
    Locale.AR: "انخفض السعر إلى {now}",
  },
  "price.rose.headline": {
    Locale.EN: "Price went up to {now}",
    Locale.FR: "Le prix a augmenté à {now}",
    Locale.AR: "ارتفع السعر إلى {now}",
  },
  "price.was": {
    Locale.EN: "It was {was}.",
    Locale.FR: "Il était de {was}.",
    Locale.AR: "كان {was}.",
  },
  "price.set.headline": {
    Locale.EN: "Price is now {now}",
    Locale.FR: "Le prix est maintenant de {now}",
    Locale.AR: "السعر الآن {now}",
  },
  "price.set.never_shown": {
    Locale.EN: "It previously had no price shown.",
    Locale.FR: "Aucun prix n'était affiché auparavant.",
    Locale.AR: "لم يكن يعرض أي سعر من قبل.",
  },
  "price.gone.headline": {
    Locale.EN: "No longer shows a price",
    Locale.FR: "N'affiche plus de prix",
    Locale.AR: "لم يعد يعرض سعرًا",
  },
  "price.gone.never_numbered": {
    Locale.EN: "The site is no longer showing a number for it.",
    Locale.FR: "Le site n'affiche plus aucun montant pour ce produit.",
    Locale.AR: "لم يعد الموقع يعرض أي مبلغ له.",
  },

  # --- framing ---------------------------------------------------------
  "product.changed.title": {
    Locale.EN: "Product {id} changed",
    Locale.FR: "Le produit {id} a changé",
    Locale.AR: "تغيّر المنتج {id}",
  },
  "product.changed.intro": {
    Locale.EN: "Product {id} changed:",
    Locale.FR: "Le produit {id} a changé :",
    Locale.AR: "تغيّر المنتج {id}:",
  },
  "product.watching_footer": {
    Locale.EN: "You are watching this product.",
    Locale.FR: "Vous surveillez ce produit.",
    Locale.AR: "أنت تتابع هذا المنتج.",
  },

  # --- telegram --------------------------------------------------------
  "telegram.linked": {
    Locale.EN: "Linked to {username}. This chat will get your notifications.",
    Locale.FR: "Chat lié à {username}. Vos notifications arriveront ici.",
    Locale.AR: "تم الربط بـ {username}. ستصل إليك إشعاراتك في هذه الدردشة.",
  },
}
