import type { MessageKey } from './en'

/** French.
 *
 * Typed as a complete `MessageKey` map, so a key added to `en` and forgotten
 * here is a compile error rather than an English string leaking into a French
 * page. The runtime fallback in `t` still exists for a key that is present but
 * empty; this is what stops the omission reaching that far.
 *
 * French typography: a non-breaking space before a colon, and « » around quoted
 * words. Those are not decoration — French sets a space before a high
 * punctuation mark, and using the English straight apostrophe reads as foreign.
 */
export const fr: Record<MessageKey, string> = {
  // --- app chrome -----------------------------------------------------
  'app.name': 'Sawa9ly API',
  'app.dashboard': 'Tableau de bord de l’API Sawa9ly',

  'nav.catalogue': 'Catalogue',
  'nav.workspace': 'Espace de travail',
  'nav.administration': 'Administration',
  'nav.products': 'Produits',
  'nav.orders': 'Commandes',
  'nav.clients': 'Clients',
  'nav.pages': 'Pages',
  'nav.users': 'Utilisateurs',
  'nav.keys': 'Clés API',
  'nav.profile': 'Mon profil',
  'nav.brand': 'Sawa9ly',
  'nav.brandSuffix': 'API',
  'nav.open': 'Ouvrir la navigation',
  'nav.group.products': 'Produits',

  'menu.open': 'Passer au thème {language}',
  'menu.profile': 'Mon profil',
  'menu.signOut': 'Se déconnecter',
  'menu.account': 'Compte',

  // --- sign in --------------------------------------------------------
  'login.title': 'Connexion',
  'login.subtitle': 'Le tableau de bord de l’API Sawa9ly.',
  'login.username': 'Nom d’utilisateur',
  'login.password': 'Mot de passe',
  'login.passwordHint': 'Votre mot de passe du tableau de bord, pas celui de sawa9ly.',
  'login.submit': 'Se connecter',
  'login.busy': 'Connexion…',
  'login.failed': 'Échec de la connexion.',

  // --- generic --------------------------------------------------------
  'generic.cancel': 'Annuler',
  'generic.close': 'Fermer',
  'generic.save': 'Enregistrer',
  'generic.saving': 'Enregistrement…',
  'generic.create': 'Créer',
  'generic.creating': 'Création…',
  'generic.delete': 'Supprimer',
  'generic.revoke': 'Révoquer',
  'generic.edit': 'Modifier',
  'generic.issue': 'Émettre une clé',
  'generic.issuing': 'Émission…',
  'generic.done': 'Terminé',
  'generic.copy': 'Copier',
  'generic.you': '(vous)',
  'generic.loading': 'Chargement…',
  'generic.never': 'jamais',
  'generic.unknown': '—',
  'generic.yes': 'oui',
  'generic.no': 'non',
  'generic.optional': 'Facultatif.',

  // --- loading and errors ---------------------------------------------
  'loading.session': 'Vérification de votre session',
  'loading.products': 'Chargement des produits',
  'loading.orders': 'Chargement des commandes',
  'loading.users': 'Chargement des utilisateurs',
  'loading.keys': 'Chargement des clés',
  'loading.recipients': 'Chargement des destinataires',
  'loading.pages': 'Chargement des pages',
  'loading.profile': 'Chargement de votre profil',
  'loading.telegram': 'Chargement de votre lien Telegram',
  'loading.product': 'Chargement du produit {id}',
  'loading.order': 'Chargement de la commande {id}',

  'error.products': 'Impossible de charger le catalogue.',
  'error.orders': 'Impossible de charger les commandes.',
  'error.users': 'Impossible de charger les utilisateurs.',
  'error.keys': 'Impossible de charger les clés API.',
  'error.recipients': 'Impossible de charger vos destinataires.',
  'error.pages': 'Impossible de charger vos pages.',
  'error.profile': 'Impossible de charger votre profil.',
  'error.telegram': 'Impossible de lire votre lien Telegram.',
  'error.product': 'Impossible de charger le produit.',
  'error.order': 'Impossible de charger la commande.',
  'error.orderId': '« {id} » n’est pas un identifiant de commande.',
  'error.productId': '« {id} » n’est pas un identifiant de produit.',

  // --- failed requests ------------------------------------------------

  'error.signedOut': 'Connectez-vous à nouveau pour continuer.',
  'error.notAllowed': 'Votre compte n’est pas autorisé à faire cela.',
  'error.notFound': 'Cela n’existe pas.',
  'error.conflict': 'Ce n’est pas possible pour le moment.',
  'error.siteUnreachable':
    'sawa9ly.app est injoignable. Réessayez dans un instant.',
  'login.wrong': 'Nom d’utilisateur ou mot de passe incorrect.',

  // --- products -------------------------------------------------------
  'products.title': 'Produits',
  'products.fetchLabel': 'Identifiant du produit',
  'products.fetchPlaceholder': '5663',
  'products.fetchAria': 'Identifiant du produit à récupérer',
  'products.fetchSubmit': 'Récupérer du site',
  'products.fetchBusy': 'Récupération…',
  'products.fetchHint':
    'Récupère une page produit depuis sawa9ly et l’enregistre ici. Seuls les produits que vous avez récupérés apparaissent ci-dessous.',
  'products.fetchInvalid': 'Saisissez l’identifiant numérique du produit, par exemple 5663.',
  'products.fetchFailed': 'Impossible de récupérer le produit.',
  'products.notFound':
    'Le produit {id} n’existe pas sur sawa9ly.app. Vérifiez l’identifiant dans l’URL du produit sur le site.',
  'products.empty': 'Rien d’enregistré pour l’instant. Récupérez un produit par son identifiant ci-dessus.',
  'products.emptySearch': 'Aucun produit ne correspond à cette recherche.',
  'products.emptyCli': 'Ou lancez :',
  'products.fetched': 'Produit {id} récupéré.',
  'products.col.id': 'Id',
  'products.col.title': 'Titre',
  'products.col.cost': 'Coût',
  'products.col.price': 'Prix de vente',
  'products.col.margin': 'Marge',
  'products.col.available': 'Disponible',
  'products.col.images': 'Images',
  'products.col.watch': 'Suivi',
  'products.watching': 'Suivi du produit {id}.',
  'products.stopped': 'Suivi du produit {id} arrêté.',

  'product.back': 'Retour',
  'product.details': 'Détails',
  'product.description': 'Description',
  'product.images': 'Images',
  'product.figures': 'Figures',
  'product.factId': 'Identifiant',
  'product.factCost': 'Coût',
  'product.factPrice': 'Prix de vente',
  'product.factMargin': 'Marge',
  'product.factAvailable': 'Disponible',
  'product.factCategories': 'Catégories',
  'product.factImages': 'Images',
  'product.factFigures': 'Figures',
  'product.editPrice': 'Modifier le prix',
  'product.priceTitle': 'Prix de vente du produit {id}',
  'product.fieldCost': 'Coût',
  'product.fieldCostHint': 'Ce que le site facture. En lecture seule, actualisé à chaque récupération.',
  'product.fieldPrice': 'Prix de vente',
  'product.fieldMargin': 'Marge',
  'product.priceFailed': 'Impossible d’enregistrer le prix.',
  'product.missing':
    'Ce produit n’est pas dans le catalogue. Le récupérer lit sa page sur sawa9ly et en enregistre le résultat.',
  'product.backToList': 'Retour aux produits',
  'product.watchingBanner':
    'Ce produit est suivi. La file le vérifie à chaque passage et y note l’heure, si bien qu’un changement de prix ou de disponibilité est détecté sans recharger la page.',
  'product.watchFailed': 'Impossible de modifier le suivi.',
  'product.enlarge': 'Agrandir l’image {position} sur {total}',

  // --- store ----------------------------------------------------------
  'store.title': 'Boutique',
  'store.optional': 'Facultatif. Les deux noms sont nécessaires pour que la boutique soit publique.',
  'store.fieldName': 'Nom de la boutique',
  'store.fieldNameHint': 'Le nom que voient les clients.',
  'store.fieldSlug': 'Nom technique',
  'store.fieldSlugHint': 'Utilisé dans l’URL. Lettres minuscules, chiffres et traits d’union.',
  'store.fieldLogo': 'Logo',
  'store.fieldLogoHint': 'Une image PNG, JPEG, WebP ou GIF, jusqu’à 256 Ko.',
  'store.removeLogo': 'Retirer le logo',
  'store.urlPreview': 'Adresse publique : /stores/{slug}',
  'store.errorType': 'Utilisez une image PNG, JPEG, WebP ou GIF.',
  'store.errorSize': 'L’image dépasse 256 Ko.',
  'profile.store': 'Boutique',
  'profile.storeHint': 'Une page publique pour vos produits, avec un formulaire de commande. Les deux noms sont nécessaires.',
  'profile.storeSaved': 'Boutique enregistrée.',
  'users.col.store': 'Boutique',

  'gallery.zoomOut': 'Dézoomer',
  'gallery.zoomIn': 'Zoomer',
  'gallery.zoomReset': 'Réinitialiser le zoom',

  // --- orders ---------------------------------------------------------
  'orders.title': 'Commandes',
  'orders.everyone': 'Tous les utilisateurs',
  'orders.superBanner':
    'Toutes les commandes de tous les utilisateurs sont affichées, car vous êtes super. Modifier ou passer la commande de quelqu’un d’autre reste une opération en ligne de commande sur son propre compte.',
  'orders.emptyAll': 'Aucune commande de la part de personne.',
  'orders.empty': 'Aucune commande pour l’instant.',
  'orders.emptySearch': 'Aucune commande ne correspond à cette recherche.',
  'orders.emptyCli': 'Démarrez-en une avec :',
  'orders.col.id': 'Id',
  'orders.col.user': 'Utilisateur',
  'orders.col.created': 'Créée le',
  'orders.col.state': 'État',
  'orders.col.client': 'Client',
  'orders.col.reference': 'Référence',
  'orders.col.lines': 'Lignes',
  'orders.col.total': 'Total',
  'orders.state.draft': 'brouillon',
  'orders.state.confirmed': 'confirmée',
  'orders.state.done': 'terminée',
  'orders.state.cancelled': 'annulée',

  'order.back': 'Retour',
  'order.title': 'Commande {id}',
  'order.draftBanner':
    'Cette commande est encore un brouillon. Ses lignes peuvent être modifiées et elle peut être envoyée à sawa9ly depuis la ligne de commande ou l’API.',
  'order.details': 'Détails',
  'order.note': 'Note',
  'order.factState': 'État',
  'order.factBy': 'Passée par',
  'order.factCreated': 'Créée le',
  'order.factClient': 'Client',
  'order.factReference': 'Référence',
  'order.factTotal': 'Total',
  'order.notSubmitted': 'non envoyée',
  'order.col.product': 'Produit',
  'order.col.title': 'Titre',
  'order.col.quantity': 'Quantité',
  'order.col.origin': 'Prix d’origine',
  'order.col.price': 'Prix',
  'order.col.subtotal': 'Sous-total',
  'order.noLines': 'Aucune ligne.',

  // --- clients --------------------------------------------------------
  'clients.title': 'Destinataires de livraison',
  'clients.add': 'Ajouter un destinataire',
  'clients.intro':
    'Ce sont les informations auxquelles une commande est livrée. Elles sont enregistrées sur votre compte, de sorte qu’une commande n’a pas à les redemander. Enregistrer un nom déjà présent met à jour ce destinataire au lieu d’en ajouter un second.',
  'clients.empty': 'Aucun pour l’instant. Ajoutez-en un ci-dessus.',
  'clients.emptySearch': 'Aucun client ne correspond à cette recherche.',
  'clients.emptyCli': 'Ou depuis la ligne de commande :',
  'clients.col.name': 'Nom',
  'clients.col.phone': 'Téléphone',
  'clients.col.adresse': 'Adresse',
  'clients.col.wilaya': 'Wilaya',
  'clients.col.commune': 'Commune',

  'clients.saved': '{name} enregistré.',
  'clients.saveFailed': 'Impossible d’enregistrer le destinataire.',
  'client.modalTitle': 'Ajouter un destinataire de livraison',
  'client.fieldName': 'Nom complet',
  'client.fieldNameHint':
    'C’est la clé. Enregistrer à nouveau ce nom met à jour ce destinataire au lieu d’en ajouter un second.',
  'client.fieldPhone': 'Téléphone',
  'client.fieldPhoneHint': 'Le numéro que le site appelle pour confirmer la livraison.',
  'client.fieldAdresse': 'Adresse',
  'client.fieldAdresseHint': 'L’adresse postale, telle que le site la formulera.',
  'client.fieldWilaya': 'Wilaya',
  'client.fieldWilayaHint':
    'La numérotation et le nom du site. Elle détermine les communes disponibles ci-dessous.',
  'client.fieldCommune': 'Commune',
  'client.fieldCommuneHint':
    'Le site le vérifie par rapport à la wilaya au moment de la commande : il doit donc venir de la liste ci-dessus.',


  'client.submit': 'Enregistrer le destinataire',
  'client.busy': 'Enregistrement…',

  // --- delivery prices --------------------------------------------------
  'nav.shipping': 'Livraison',
  // --- wilayas and communes --------------------------------------------
  'client.pickWilaya':
    'Choisir une wilaya',
  'client.pickCommune':
    'Choisir une commune',
  'client.pickWilayaFirst':
    'Choisissez d’abord une wilaya',
  'loading.wilayas':
    'Chargement des wilayas',
  'loading.communes':
    'Chargement des communes',
  'error.wilayas':
    'Impossible de charger les wilayas.',
  'error.communes':
    'Impossible de charger les communes de cette wilaya.',

  'shipping.title': 'Frais de livraison',
  'shipping.intro':
    'Ce que le site facture pour livrer dans chaque wilaya, tel que lors de la dernière synchronisation. Une liste unique pour tout le monde : elle n’est donc pas à vous de la modifier — la rafraîchir est une commande sur le serveur.',
  'shipping.col.wilaya': 'Wilaya',
  'shipping.col.wilayaId': 'N°',
  'shipping.col.available': 'Desservie',
  'shipping.col.price': 'Livraison à domicile',
  'shipping.col.officePrice': 'Retrait au bureau',
  'shipping.notServed': 'non desservie',
  'shipping.filterLabel': 'Filtrer par couverture',
  'shipping.filter.all': 'Toutes',
  'shipping.filter.available': 'Desservies',
  'shipping.filter.unavailable': 'Non desservies',
  'shipping.empty': 'Aucun frais enregistré pour l’instant.',
  'shipping.emptyFiltered':
    'Aucune wilaya dans cette sélection. Chaque wilaya est soit desservie, soit non desservie : l’une des deux autres filtres affichera des lignes.',
  'shipping.sync':    'Récupérer les tarifs',
  'shipping.syncing':
    'Récupération…',
  'shipping.synced':
    '{count} wilayas récupérées depuis sawa9ly.',
  'shipping.emptyFetch':
    'Récupérez-les avec le bouton ci-dessus, ou en ligne de commande :',
  'error.shippingSync':
    'Impossible de récupérer les tarifs depuis sawa9ly.',

  'shipping.emptyCli': 'Enregistrez-les avec :',
  'loading.shipping': 'Chargement des frais de livraison',
  'error.shipping': 'Impossible de charger les frais de livraison.',

  // --- landing pages --------------------------------------------------
  'pages.title': 'Pages d’atterrissage',
  'pages.new': 'Nouvelle page',
  'pages.intro':
    'Vos propres pages, une par produit ou autant que vous voulez pour le même produit. Rien ne sert encore de page — c’est ici que le texte est conservé en attendant.',
  'pages.empty': 'Aucune pour l’instant. Créez-en une ci-dessus.',
  'pages.emptySearch': 'Aucune page ne correspond à cette recherche.',
  'pages.emptyCli': 'Ou depuis la ligne de commande :',
  'pages.col.title': 'Titre',
  'pages.col.product': 'Produit',
  'pages.col.state': 'État',
  'pages.col.link': 'Lien public',
  'pages.col.html': 'HTML',
  'pages.col.updated': 'Mis à jour',
  'pages.removedFromCatalogue': 'retiré du catalogue',
  'pages.notServed': 'Seule une page publiée est servie',
  'pages.created': '« {title} » créée.',
  'pages.saved': 'Enregistré.',
  'pages.createFailed': 'Impossible de créer la page.',
  'pages.saveFailed': 'Impossible d’enregistrer la page.',
  'pages.state.publish': 'publiée',
  'pages.state.draft': 'brouillon',
  'pages.state.archive': 'archivée',

  'page.modalTitle': 'Nouvelle page d’atterrissage',
  'page.fieldProduct': 'Produit',
  'page.fieldProductHint':
    'C’est l’identifiant sawa9ly qui est enregistré. Un produit absent de la liste peut aussi être ajouté en saisissant son identifiant.',
  'page.fieldProductHintEmpty':
    'Rien d’enregistré dans le catalogue pour l’instant. Saisissez l’identifiant sawa9ly du produit.',
  'page.fieldTitle': 'Titre',
  'page.fieldTitleHint': 'Le nom de la page dans cette liste.',
  'page.fieldHtml': 'HTML',
  'page.fieldHtmlHint':
    'Le balisage de la page, enregistré tel qu’écrit. Rien ne le rend encore, il ne peut donc pas casser ce tableau de bord.',
  'page.submit': 'Créer la page',
  'page.busy': 'Création…',
  'page.editTitle': 'Modifier la page',
  'page.editProductGone': 'Le produit de cette page n’est plus dans le catalogue.',
  'page.editForProduct': 'Pour le produit {id}',
  'page.fieldLink': 'Lien public',
  'page.fieldLinkHintPublished':
    'En ligne à l’adresse /pages/. Ouvrez-la dans un nouvel onglet pour voir ce que voit un visiteur.',
  'page.fieldLinkHintDraft':
    'Pas encore servie — seules les pages à l’état « publiée » répondent à cette adresse.',
  'page.fieldEditTitle': 'Titre de la page',
  'page.fieldEditTitleHint': 'Le nom de cette page dans votre liste.',
  'page.fieldState': 'État',
  'page.fieldStateHint':
    'Seul « publiée » est en ligne. « archivée » conserve la page sans la servir.',
  'page.fieldEditHtml': 'HTML',
  'page.fieldEditHtmlHint':
    'Le balisage de la page. Vider ce champ vide réellement la page — c’est un changement à part entière, pas un champ laissé tel quel.',

  // --- profile --------------------------------------------------------
  'profile.title': 'Mon profil',
  'profile.language': 'Langue',
  'profile.languageLight': 'le thème clair',
  'profile.languageDark': 'le thème sombre',
  'profile.languageHint':
    'Le tableau de bord est rédigé dans cette langue, et vos notifications vous parviennent dans cette langue aussi.',
  'profile.language.en': 'Anglais',
  'profile.language.fr': 'Français',
  'profile.language.ar': 'Arabe',
  'profile.sawa9ly': 'Compte sawa9ly',
  'profile.sawa9lyHas':
    'Les identifiants sont enregistrés, ce compte peut donc passer des commandes.',
  'profile.sawa9lyHasNot':
    'Ajoutez-les pour que ce compte puisse passer des commandes. Personne d’autre ne peut les saisir à votre place.',
  'profile.siteSession': 'Session du site',
  'profile.sessionReady': 'prête',
  'profile.sessionNone': 'aucune',
  'profile.logIn': 'Se connecter à sawa9ly',
  'profile.logInBusy': 'Connexion…',
  'profile.logInFailed': 'Impossible de se connecter à sawa9ly.',
  'profile.logInNeedsCredentials':
    'Ajoutez d’abord votre adresse e-mail et votre mot de passe sawa9ly',
  'profile.changeDetails': 'Modifier vos informations',
  'profile.fieldEmail': 'Adresse e-mail sawa9ly',
  'profile.fieldEmailHint': 'Laissez vide pour conserver l’adresse actuelle.',
  'profile.fieldSawa9lyPassword': 'Mot de passe sawa9ly',
  'profile.fieldSawa9lyPasswordHint': 'Laissez vide pour conserver le mot de passe actuel.',
  'profile.fieldDashboardPassword': 'Mot de passe du tableau de bord',
  'profile.fieldDashboardPasswordHint':
    'Celui qui vous permet de vous connecter ici. Laissez vide pour conserver l’actuel.',
  'profile.saveChanges': 'Enregistrer les modifications',
  'profile.busy': 'Enregistrement…',
  'profile.saved': 'Enregistré.',
  'profile.nothingToSave': 'Rien à enregistrer.',
  'profile.saveFailed': 'Impossible d’enregistrer votre profil.',

  // --- telegram -------------------------------------------------------
  'telegram.title': 'Notifications Telegram',
  'telegram.bound': 'Les notifications sont envoyées à {chat} ({type}).',
  'telegram.test': 'Envoyer un message de test',
  'telegram.testBusy': 'Envoi…',
  'telegram.testSent': 'Envoyé. Vérifiez la discussion.',
  'telegram.testFailed': 'Impossible d’envoyer le message de test.',
  'telegram.unbind': 'Délier cette discussion',
  'telegram.unbound': 'Impossible de délier votre discussion.',
  'telegram.unboundIntro':
    'Liez une discussion privée au robot : vos notifications y arriveront. Un canal privé dont vous êtes propriétaire fonctionne aussi, avec le robot ajouté comme administrateur.',
  'telegram.pending': 'En attente de l’ouverture du lien par vos soins.',
  'telegram.expires': 'expire à {time}',
  'telegram.getLink': 'Obtenir un lien',
  'telegram.getNewLink': 'Obtenir un nouveau lien',
  'telegram.working': 'Traitement…',
  'telegram.linkFailed':
    'Impossible de créer un lien. TELEGRAM_BOT_TOKEN est-il défini ?',
  'telegram.linkIntro':
    'Ouvrez ce lien, puis appuyez sur {action} sur la page qui s’affiche. Il n’est montré qu’une fois et ne peut pas être récupéré.',
  'telegram.openInWeb': 'Open in Web',
  'telegram.codeLine':
    'Code {code}, valable jusqu’à {time}. Il cesse de fonctionner une fois utilisé ou à son expiration.',
  'telegram.notStartBot':
    'N’appuyez pas sur {action} — ce bouton exige que Telegram soit installé sur cet ordinateur et ne fait rien du tout sans. {action} fonctionne dans les deux cas. Si vous préférez ne pas utiliser le lien, ouvrez le robot dans l’application Telegram ou sur {site} et envoyez {code} comme message.',
  'telegram.startBot': 'Start Bot',
  'telegram.listenHint':
    'Rien n’arrive tant que l’écouteur ci-dessous n’est pas lancé — c’est lui qui reçoit le message.',

  // --- API keys -------------------------------------------------------
  'keys.title': 'Clés API',
  'keys.filterUsable': 'utilisables seulement',
  'keys.createFirst': 'Créez d’abord un utilisateur',
  'keys.adminBanner':
    'Vous voyez les clés de tous les utilisateurs. Émettre une clé au nom de quelqu’un d’autre exige le rôle super — vous pouvez toujours émettre les vôtres.',
  'keys.noKeys': 'Aucune clé pour l’instant.',
  'keys.noUsable': 'Aucune clé utilisable.',
  'keys.col.prefix': 'Préfixe',
  'keys.col.type': 'Type',
  'keys.col.label': 'Libellé',
  'keys.col.user': 'Utilisateur',
  'keys.col.state': 'État',
  'keys.col.lastUsed': 'Dernière utilisation',
  'keys.col.expires': 'Expire',
  'keys.revoked': 'Clé {prefix}… révoquée.',
  'keys.revokeFailed': 'Impossible de révoquer la clé.',
  'keys.issueFailed': 'Impossible d’émettre la clé.',
  'keys.state.active': 'active',
  'keys.state.expired': 'expirée',
  'keys.state.revoked': 'révoquée',

  'key.issueTitle': 'Émettre une clé API',
  'key.issueSelfTitle': 'Émettez-vous une clé API',
  'key.fieldUser': 'Utilisateur',
  'key.fieldType': 'Type',
  'key.fieldTypeHint':
    'Une clé n’ouvre qu’une seule surface. Une clé api sert aux scripts qui appellent /api ; une clé mcp sert à un agent IA et fonctionne uniquement sur le serveur MCP.',
  'key.type.api': 'API',
  'key.type.mcp': 'MCP',
  'key.fieldLabel': 'Libellé',
  'key.fieldLabelHint': 'Facultatif. Utile pour se souvenir à quoi sert la clé.',
  'key.fieldExpires': 'Expire dans (jours)',
  'key.fieldExpiresHint': 'Laissez vide pour une clé qui n’expire jamais.',
  'key.plaintextHint':
    'Le texte en clair s’affiche une seule fois, juste après, et ne peut pas être relu.',
  'key.revealTitle': 'Copiez cette clé maintenant',
  'key.revealBanner':
    'C’est la seule fois que la clé s’affiche. Le serveur n’en conserve qu’une empreinte, elle ne pourra donc plus être affichée — si vous la perdez, émettez-en une nouvelle.',
  'key.revokeTitle': 'Révoquer {prefix}… ?',
  'key.revokeBody':
    'Tout client qui utilise cette clé cessera immédiatement de fonctionner. L’enregistrement reste, pour que vous puissiez voir que la clé a existé.',
  'key.revokeConfirm': 'Révoquer la clé',

  // --- users ----------------------------------------------------------
  'users.title': 'Utilisateurs',
  'users.add': 'Ajouter un utilisateur',
  'users.adminBanner':
    'En tant qu’administrateur, vous pouvez ajouter des utilisateurs. Modifier ou supprimer un compte existant exige le rôle super.',
  'users.added': 'Utilisateur ajouté.',
  'users.updated': 'Utilisateur mis à jour.',
  'users.deleted': '{name} supprimé.',
  'users.createFailed': 'Impossible de créer l’utilisateur.',
  'users.saveFailed': 'Impossible d’enregistrer l’utilisateur.',
  'users.deleteFailed': 'Impossible de supprimer l’utilisateur.',
  'users.superManaged': 'Un compte super se gère depuis la ligne de commande',
  'users.cannotDeleteSelf': 'Vous ne pouvez pas supprimer votre propre compte',
  'users.col.username': 'Nom d’utilisateur',
  'users.col.role': 'Rôle',
  'users.col.sawa9ly': 'Sawa9ly',
  'users.col.telegram': 'Telegram',
  'users.col.keys': 'Clés',
  'users.col.orders': 'Commandes',
  'users.col.dashboard': 'Tableau de bord',
  'users.set': 'saisis',
  'users.notSet': 'non saisis',
  'users.canSignIn': 'connexion possible',
  'users.noPassword': 'aucun mot de passe',

  'user.modalTitle': 'Ajouter un utilisateur',
  'user.fieldUsername': 'Nom d’utilisateur',
  'user.fieldRole': 'Rôle',
  'user.fieldPassword': 'Mot de passe du tableau de bord',
  'user.fieldPasswordHint': 'Laissez vide pour créer un utilisateur réservé à l’API.',
  'user.newUserNote':
    'Le nouvel utilisateur définit lui-même son adresse e-mail sawa9ly, son mot de passe sawa9ly et sa discussion Telegram depuis son profil.',
  'user.submit': 'Créer l’utilisateur',
  'user.busy': 'Création…',
  'user.editTitle': 'Modifier {name}',
  'user.editSuperBody':
    '{name} est un compte {role}. Les comptes super se gèrent depuis l’environnement ou la ligne de commande, pas depuis le tableau de bord.',
  'user.fieldRoleSelf': 'Vous ne pouvez pas modifier votre propre rôle.',
  'user.fieldNewPassword': 'Nouveau mot de passe du tableau de bord',
  'user.fieldNewPasswordSelf': 'Laissez vide pour conserver le mot de passe actuel.',
  'user.fieldNewPasswordOther':
    'Laissez vide pour conserver le mot de passe actuel. Son adresse e-mail et son mot de passe sawa9ly lui appartiennent : il les définit depuis son profil.',
  'user.deleteTitle': 'Supprimer {name} ?',
  'user.deleteBody':
    'Cela supprime l’utilisateur, ses clés API, ses clients et toutes ses commandes. C’est irréversible.',
  'user.deleteConfirm': 'Supprimer l’utilisateur',
  'users.emptySearch': 'Aucun utilisateur ne correspond à cette recherche.',

  // --- roles, as shown in a badge --------------------------------------
  'role.user': 'utilisateur',
  'role.admin': 'administrateur',
  'role.super': 'super',
  'key.emptySearch': 'Aucune clé API ne correspond à cette recherche.',

  // --- searching and paging a list --------------------------------------
  // Shared by all six list screens, which is why these are not per-resource.
  'list.search': 'Rechercher',
  'list.searchBy': 'Rechercher des {resource}',
  'list.clearSearch': 'Effacer la recherche',
  'list.previous': 'Précédent',
  'list.next': 'Suivant',
  'list.page': 'Page {page} sur {pages}',
  'list.showing': 'Affichage de {from} à {to} sur {total}',
  'list.onePage': 'Les {total} affichés',
  'list.searching': 'Recherche…',

  'resource.products': 'produits',
  'resource.orders': 'commandes',
  'resource.users': 'utilisateurs',
  'resource.keys': 'clés API',
  'resource.clients': 'clients',
  'resource.pages': 'pages',
  'resource.shipping': 'frais de livraison',
}
