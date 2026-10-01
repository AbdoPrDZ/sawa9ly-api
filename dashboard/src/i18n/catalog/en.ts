/** English, and the reference: every other catalogue is checked against this one.
 *
 * Keys are names, not sentences. An English string is not a stable identifier —
 * rewording "Sign in" must not orphan the Arabic and French versions of it — so
 * nothing is ever found by matching prose.
 *
 * `{name}` fields are filled by `t`. A field that is not supplied is a sentence
 * with a hole in it, so a missing one throws rather than rendering literally.
 */
export const en = {
  // --- app chrome -----------------------------------------------------
  'app.name': 'Sawa9ly API',
  'app.dashboard': 'Sawa9ly API Dashboard',

  'nav.catalogue': 'Catalogue',
  'nav.workspace': 'Workspace',
  'nav.administration': 'Administration',
  'nav.products': 'Products',
  'nav.orders': 'Orders',
  'nav.clients': 'Clients',
  'nav.pages': 'Pages',
  'nav.users': 'Users',
  'nav.keys': 'API keys',
  'nav.profile': 'My profile',
  'nav.brand': 'Sawa9ly',
  'nav.brandSuffix': 'API',
  'nav.open': 'Open navigation',
  'nav.group.products': 'Products',

  'menu.open': 'Switch to {language} theme',
  'menu.profile': 'My profile',
  'menu.signOut': 'Sign out',
  'menu.account': 'Account',

  // --- sign in --------------------------------------------------------
  'login.title': 'Sign in',
  'login.subtitle': 'The Sawa9ly API dashboard.',
  'login.username': 'Username',
  'login.password': 'Password',
  'login.passwordHint': 'Your dashboard password, not the sawa9ly one.',
  'login.submit': 'Sign in',
  'login.busy': 'Signing in…',
  'login.failed': 'Sign in failed.',

  // --- generic --------------------------------------------------------
  'generic.cancel': 'Cancel',
  'generic.close': 'Close',
  'generic.save': 'Save',
  'generic.saving': 'Saving…',
  'generic.create': 'Create',
  'generic.creating': 'Creating…',
  'generic.delete': 'Delete',
  'generic.revoke': 'Revoke',
  'generic.edit': 'Edit',
  'generic.issue': 'Issue key',
  'generic.issuing': 'Issuing…',
  'generic.done': 'Done',
  'generic.copy': 'Copy',
  'generic.you': '(you)',
  'generic.loading': 'Loading…',
  'generic.never': 'never',
  'generic.unknown': '—',
  'generic.yes': 'yes',
  'generic.no': 'no',
  'generic.optional': 'Optional.',

  // --- loading and errors ---------------------------------------------
  'loading.session': 'Checking your session',
  'loading.products': 'Loading products',
  'loading.orders': 'Loading orders',
  'loading.users': 'Loading users',
  'loading.keys': 'Loading keys',
  'loading.recipients': 'Loading recipients',
  'loading.pages': 'Loading pages',
  'loading.profile': 'Loading your profile',
  'loading.telegram': 'Loading your Telegram link',
  'loading.product': 'Loading product {id}',
  'loading.order': 'Loading order {id}',

  'error.products': 'Could not load the catalogue.',
  'error.orders': 'Could not load the orders.',
  'error.users': 'Could not load users.',
  'error.keys': 'Could not load API keys.',
  'error.recipients': 'Could not load your recipients.',
  'error.pages': 'Could not load your pages.',
  'error.profile': 'Could not load your profile.',
  'error.telegram': 'Could not read your Telegram link.',
  'error.product': 'Could not load the product.',
  'error.order': 'Could not load the order.',
  'error.orderId': '“{id}” is not an order id.',
  'error.productId': '“{id}” is not a product id.',

  // --- failed requests ------------------------------------------------
  // Chosen from the HTTP status, because the server's own `detail` is English
  // and the API has no per-language messages. See `i18n/apiError.ts`.

  'error.signedOut': 'Sign in again to continue.',
  'error.notAllowed': 'Your account is not allowed to do that.',
  'error.notFound': 'There is no such thing.',
  'error.conflict': 'That cannot be done right now.',
  'error.siteUnreachable':
    'sawa9ly.app could not be reached. Try again in a moment.',
  'login.wrong': 'Wrong username or password.',

  // --- products -------------------------------------------------------
  'products.title': 'Products',
  'products.fetchLabel': 'Product id',
  'products.fetchPlaceholder': '5663',
  'products.fetchAria': 'Product id to fetch',
  'products.fetchSubmit': 'Fetch from site',
  'products.fetchBusy': 'Fetching…',
  'products.fetchHint':
    'Fetches a product page from sawa9ly and stores it here. Only products you have fetched appear below.',
  'products.fetchInvalid': 'Enter the numeric product id, e.g. 5663.',
  'products.fetchFailed': 'Could not fetch the product.',
  'products.notFound':
    'Product {id} does not exist on sawa9ly.app. Check the id in the product’s URL on the site.',
  'products.emptySearch': 'No products match that search.',
'products.empty': 'Nothing saved yet. Fetch a product by its id above.',
  'products.emptyCli': 'Or run:',
  'products.fetched': 'Fetched product {id}.',
  'products.col.id': 'Id',
  'products.col.title': 'Title',
  'products.col.price': 'Price',
  'products.col.available': 'Available',
  'products.col.images': 'Images',
  'products.col.watch': 'Watch',
  'products.watching': 'Watching product {id}.',
  'products.stopped': 'Stopped watching {id}.',

  'product.back': 'Back',
  'product.details': 'Details',
  'product.description': 'Description',
  'product.factId': 'Product id',
  'product.factPrice': 'Price',
  'product.factAvailable': 'Available',
  'product.factCategories': 'Categories',
  'product.factImages': 'Images',
  'product.factFigures': 'Figures',
  'product.missing':
    'This product is not in the catalogue. Fetching it reads its page from sawa9ly and stores the result.',
  'product.backToList': 'Back to products',
  'product.watchingBanner':
    'Watching this product. The queue checks it every pass and stamps the time here, so a price or availability change is picked up without refreshing.',
  'product.watchFailed': 'Could not update the watch.',
  'product.enlarge': 'Enlarge image {position} of {total}',

  'gallery.zoomOut': 'Zoom out',
  'gallery.zoomIn': 'Zoom in',
  'gallery.zoomReset': 'Reset zoom',

  // --- orders ---------------------------------------------------------
  'orders.title': 'Orders',
  'orders.everyone': 'Every user',
  'orders.superBanner':
    'Showing every user’s orders, because you are a super. Editing or checking out somebody else’s order stays a CLI operation on their own account.',
  'orders.emptyAll': 'No orders from anybody yet.',
  'orders.emptySearch': 'No orders match that search.',
'orders.empty': 'No orders yet.',
  'orders.emptyCli': 'Start one with:',
  'orders.col.id': 'Id',
  'orders.col.user': 'User',
  'orders.col.created': 'Created',
  'orders.col.state': 'State',
  'orders.col.client': 'Client',
  'orders.col.reference': 'Reference',
  'orders.col.lines': 'Lines',
  'orders.col.total': 'Total',
  'orders.state.draft': 'draft',
  'orders.state.confirmed': 'confirmed',
  'orders.state.done': 'done',
  'orders.state.cancelled': 'cancelled',

  'order.back': 'Back',
  'order.title': 'Order {id}',
  'order.draftBanner':
    'This order is still a draft. Its lines can be changed and it can be submitted to sawa9ly from the CLI or the API.',
  'order.details': 'Details',
  'order.note': 'Note',
  'order.factState': 'State',
  'order.factBy': 'Ordered by',
  'order.factCreated': 'Created',
  'order.factClient': 'Client',
  'order.factReference': 'Reference',
  'order.factTotal': 'Total',
  'order.notSubmitted': 'not submitted',
  'order.col.product': 'Product',
  'order.col.title': 'Title',
  'order.col.quantity': 'Quantity',
  'order.col.origin': 'Origin price',
  'order.col.price': 'Price',
  'order.col.subtotal': 'Subtotal',
  'order.noLines': 'No lines.',

  // --- clients --------------------------------------------------------
  'clients.title': 'Delivery recipients',
  'clients.add': 'Add recipient',
  'clients.intro':
    'These are the details an order is shipped to. They are stored against your account, so a checkout does not have to ask for them again. Saving a name that is already here updates that recipient instead of adding a second one.',
  'clients.emptySearch': 'No clients match that search.',
  'clients.empty': 'None yet. Add one above.',
  'clients.emptyCli': 'Or from the command line:',
  'clients.col.name': 'Name',
  'clients.col.phone': 'Phone',
  'clients.col.adresse': 'Adresse',
  'clients.col.wilaya': 'Wilaya',
  'clients.col.commune': 'Commune',
  'clients.col.note': 'Note',
  'clients.saved': 'Saved {name}.',
  'clients.saveFailed': 'Could not save the recipient.',
  'client.modalTitle': 'Add a delivery recipient',
  'client.fieldName': 'Full name',
  'client.fieldNameHint':
    'The key. Saving this name again updates that recipient instead of adding a second one.',
  'client.fieldPhone': 'Phone',
  'client.fieldPhoneHint': 'The number the site calls to confirm the delivery.',
  'client.fieldAdresse': 'Adresse',
  'client.fieldAdresseHint': 'Street address, as the site wants it written.',
  'client.fieldWilaya': 'Wilaya id',
  'client.fieldWilayaHint':
    'The site’s numeric id for the province, not its name. Needed to reach dispatch.',
  'client.fieldCommune': 'Commune id',
  'client.fieldCommuneHint': 'The site’s numeric id for the commune.',
  'client.fieldNote': 'Note',
  'client.fieldNoteHint': 'Optional. Anything worth remembering about them.',
  'client.submit': 'Save recipient',
  'client.busy': 'Saving…',

  // --- landing pages --------------------------------------------------
  'pages.title': 'Landing pages',
  'pages.new': 'New page',
  'pages.intro':
    'Your own pages, one per product or as many as you like for the same one. Nothing serves a page yet — this is where the writing is kept until it is.',
  'pages.emptySearch': 'No pages match that search.',
  'pages.empty': 'None yet. Create one above.',
  'pages.emptyCli': 'Or from the command line:',
  'pages.col.title': 'Title',
  'pages.col.product': 'Product',
  'pages.col.state': 'State',
  'pages.col.link': 'Public link',
  'pages.col.html': 'HTML',
  'pages.col.updated': 'Updated',
  'pages.removedFromCatalogue': 'removed from catalogue',
  'pages.notServed': 'Only a published page is served',
  'pages.created': 'Created “{title}”.',
  'pages.saved': 'Saved.',
  'pages.createFailed': 'Could not create the page.',
  'pages.saveFailed': 'Could not save the page.',
  'pages.state.publish': 'publish',
  'pages.state.draft': 'draft',
  'pages.state.archive': 'archive',

  'page.modalTitle': 'New landing page',
  'page.fieldProduct': 'Product',
  'page.fieldProductHint':
    'The sawa9ly id is what gets stored. A product not in the list can still be added by typing its id.',
  'page.fieldProductHintEmpty':
    'Nothing saved in the catalogue yet. Type the sawa9ly product id.',
  'page.fieldTitle': 'Title',
  'page.fieldTitleHint': 'What the page is called in this list.',
  'page.fieldHtml': 'HTML',
  'page.fieldHtmlHint':
    'The page markup, stored as written. Nothing renders it yet, so it cannot break this dashboard.',
  'page.submit': 'Create page',
  'page.busy': 'Creating…',
  'page.editTitle': 'Edit page',
  'page.editProductGone': 'This page’s product is no longer in the catalogue.',
  'page.editForProduct': 'For product {id}',
  'page.fieldLink': 'Public link',
  'page.fieldLinkHintPublished':
    'Live at /pages/. Open it in a new tab to see what a visitor sees.',
  'page.fieldLinkHintDraft':
    'Not served yet — only a page in the publish state answers this address.',
  'page.fieldEditTitle': 'Page title',
  'page.fieldEditTitleHint': 'What this page is called in your list.',
  'page.fieldState': 'State',
  'page.fieldStateHint':
    'Only publish is live. Archive keeps the page without serving it.',
  'page.fieldEditHtml': 'HTML',
  'page.fieldEditHtmlHint':
    'The page markup. Clearing this box empties the page — that is a real change, not a skipped one.',

  // --- profile --------------------------------------------------------
  'profile.title': 'My profile',
  'profile.language': 'Language',
  'profile.languageLight': 'the light theme',
  'profile.languageDark': 'the dark theme',
  'profile.languageHint':
    'The dashboard is written in this language, and your notifications arrive in it too.',
  'profile.language.en': 'English',
  'profile.language.fr': 'French',
  'profile.language.ar': 'Arabic',
  'profile.sawa9ly': 'Sawa9ly account',
  'profile.sawa9lyHas':
    'Credentials are stored, so this account can place orders.',
  'profile.sawa9lyHasNot':
    'Add these to let this account place orders. Nobody else can set them for you.',
  'profile.siteSession': 'Site session',
  'profile.sessionReady': 'ready',
  'profile.sessionNone': 'none',
  'profile.logIn': 'Log in to sawa9ly',
  'profile.logInBusy': 'Logging in…',
  'profile.logInFailed': 'Could not log in to sawa9ly.',
  'profile.logInNeedsCredentials': 'Add your sawa9ly email and password first',
  'profile.changeDetails': 'Change your details',
  'profile.fieldEmail': 'Sawa9ly email',
  'profile.fieldEmailHint': 'Leave empty to keep the current one.',
  'profile.fieldSawa9lyPassword': 'Sawa9ly password',
  'profile.fieldSawa9lyPasswordHint': 'Leave empty to keep the current one.',
  'profile.fieldDashboardPassword': 'Dashboard password',
  'profile.fieldDashboardPasswordHint':
    'How you sign in here. Leave empty to keep the current one.',
  'profile.saveChanges': 'Save changes',
  'profile.busy': 'Saving…',
  'profile.saved': 'Saved.',
  'profile.nothingToSave': 'Nothing to save.',
  'profile.saveFailed': 'Could not save your profile.',

  // --- telegram -------------------------------------------------------
  'telegram.title': 'Telegram notifications',
  'telegram.bound':
    'Notifications go to {chat} ({type}).',
  'telegram.test': 'Send a test message',
  'telegram.testBusy': 'Sending…',
  'telegram.testSent': 'Sent. Check the chat.',
  'telegram.testFailed': 'Could not send the test message.',
  'telegram.unbind': 'Unlink this chat',
  'telegram.unbound': 'Could not unlink your chat.',
  'telegram.unboundIntro':
    'Link a private chat with the bot, and it will be where your notifications arrive. A private channel you own works too, with the bot added as an admin.',
  'telegram.pending': 'Waiting for you to open the link.',
  'telegram.expires': 'expires {time}',
  'telegram.getLink': 'Get a link',
  'telegram.getNewLink': 'Get a new link',
  'telegram.working': 'Working…',
  'telegram.linkFailed': 'Could not make a link. Is TELEGRAM_BOT_TOKEN set?',
  'telegram.linkIntro':
    'Open this link, then press {action} on the page that comes up. It is shown once and cannot be recovered.',
  'telegram.openInWeb': 'Open in Web',
  'telegram.codeLine': 'Code {code}, good until {time}. It stops working once used, or when it expires.',
  'telegram.notStartBot':
    'Do not press {action} — that one needs Telegram installed on this computer, and does nothing at all without it. {action} works either way. If you would rather not use the link, open the bot in the Telegram app or at {site} and send {code} as a message.',
  'telegram.startBot': 'Start Bot',
  'telegram.listenHint':
    'Nothing arrives until the listener below is running — that is what receives the message.',

  // --- API keys -------------------------------------------------------
  'keys.title': 'API keys',
  'keys.filterUsable': 'usable only',
  'keys.createFirst': 'Create a user first',
  'keys.adminBanner':
    'You are seeing every user’s key. Issuing one in somebody else’s name needs the super role — you can still issue keys for yourself.',
  'keys.noKeys': 'No keys yet.',
  'keys.noUsable': 'No usable keys.',
  'keys.col.prefix': 'Prefix',
  'keys.col.label': 'Label',
  'keys.col.user': 'User',
  'keys.col.state': 'State',
  'keys.col.lastUsed': 'Last used',
  'keys.col.expires': 'Expires',
  'keys.revoked': 'Key {prefix}… revoked.',
  'keys.revokeFailed': 'Could not revoke the key.',
  'keys.issueFailed': 'Could not issue the key.',
  'keys.state.active': 'active',
  'keys.state.expired': 'expired',
  'keys.state.revoked': 'revoked',

  'key.issueTitle': 'Issue an API key',
  'key.issueSelfTitle': 'Issue yourself an API key',
  'key.fieldUser': 'User',
  'key.fieldLabel': 'Label',
  'key.fieldLabelHint': 'Optional. Helps you remember what the key is for.',
  'key.fieldExpires': 'Expires in days',
  'key.fieldExpiresHint': 'Leave empty for a key that never expires.',
  'key.plaintextHint':
    'The plaintext is shown once, straight after this, and cannot be read back.',
  'key.revealTitle': 'Copy this key now',
  'key.revealBanner':
    'This is the only time the key is shown. The server keeps only a hash, so it cannot be shown again — if you lose it, issue a new one.',
  'key.revokeTitle': 'Revoke {prefix}…?',
  'key.revokeBody':
    'Any client using this key stops working immediately. The record stays so you can see the key existed.',
  'key.revokeConfirm': 'Revoke key',

  // --- users ----------------------------------------------------------
  'users.title': 'Users',
  'users.add': 'Add user',
  'users.adminBanner':
    'As an administrator you can add users. Editing or deleting an existing account needs the super role.',
  'users.added': 'User added.',
  'users.updated': 'User updated.',
  'users.deleted': 'Deleted {name}.',
  'users.createFailed': 'Could not create the user.',
  'users.saveFailed': 'Could not save the user.',
  'users.deleteFailed': 'Could not delete the user.',
  'users.superManaged': 'A super account is managed from the CLI',
  'users.cannotDeleteSelf': 'You cannot delete your own account',
  'users.col.username': 'Username',
  'users.col.role': 'Role',
  'users.col.sawa9ly': 'Sawa9ly',
  'users.col.telegram': 'Telegram',
  'users.col.keys': 'Keys',
  'users.col.orders': 'Orders',
  'users.col.dashboard': 'Dashboard',
  'users.set': 'set',
  'users.notSet': 'not set',
  'users.canSignIn': 'can sign in',
  'users.noPassword': 'no password',

  'user.modalTitle': 'Add user',
  'user.fieldUsername': 'Username',
  'user.fieldRole': 'Role',
  'user.fieldPassword': 'Dashboard password',
  'user.fieldPasswordHint': 'Leave empty to create an API-only user.',
  'user.newUserNote':
    'The new user sets their own sawa9ly email, sawa9ly password and Telegram chat from their profile.',
  'user.submit': 'Create user',
  'user.busy': 'Creating…',
  'user.editTitle': 'Edit {name}',
  'user.editSuperBody':
    '{name} is a {role} account. Super accounts are managed from the environment or the CLI, not from the dashboard.',
  'user.fieldRoleSelf': 'You cannot change your own role.',
  'user.fieldNewPassword': 'New dashboard password',
  'user.fieldNewPasswordSelf': 'Leave empty to keep the current one.',
  'user.fieldNewPasswordOther':
    'Leave empty to keep the current one. Their sawa9ly email and password are their own to set, from their profile.',
  'user.deleteTitle': 'Delete {name}?',
  'user.deleteBody':
    'This removes the user, their API keys, their clients and all their orders. It cannot be undone.',
  'user.deleteConfirm': 'Delete user',
  'users.emptySearch': 'No users match that search.',

  // --- roles, as shown in a badge --------------------------------------
  'role.user': 'user',
  'role.admin': 'admin',
  'role.super': 'super',
  'key.emptySearch': 'No API keys match that search.',

  // --- searching and paging a list --------------------------------------
  // Shared by all six list screens, which is why these are not per-resource.
  'list.search': 'Search',
  'list.searchBy': 'Search {resource}',
  'list.clearSearch': 'Clear search',
  'list.previous': 'Previous',
  'list.next': 'Next',
  'list.page': 'Page {page} of {pages}',
  'list.showing': 'Showing {from}–{to} of {total}',
  'list.onePage': 'All {total} shown',
  'list.searching': 'Searching…',

  'resource.products': 'products',
  'resource.orders': 'orders',
  'resource.users': 'users',
  'resource.keys': 'API keys',
  'resource.clients': 'clients',
  'resource.pages': 'pages',
} as const

export type MessageKey = keyof typeof en
