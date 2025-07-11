{
    'name': 'Social Media Integration',
    'version': '16.0.1.0.0',
    'category': 'Tools',
    'summary': 'Manage and fetch posts from multiple social media accounts',
    'description': """
        Social Media Integration Module
        ===============================
        
        This module allows users to:
        - Connect multiple social media accounts (Twitter, Facebook)
        - Fetch posts from people they follow
        - Apply filters to the fetched content
        - Manage credentials securely for each account
    """,
    'author': 'Apexive',
    'website': 'https://www.apexive.com',
    'depends': ['base', 'mail'],
    'data': [
        'security/social_media_security.xml',
        'security/ir.model.access.csv',
        'data/social_media_provider_data.xml',
        'data/social_media_cron.xml',
        'views/social_media_menu.xml',
        'views/social_media_provider_views.xml',
        'views/social_media_account_views.xml',
        'views/social_media_profile_views.xml',
        'views/social_media_post_views.xml',
        'views/social_media_filter_views.xml',
        'wizard/social_media_oauth_wizard_views.xml',
        'templates/oauth_success.xml',
        'templates/oauth_error.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'social_media/static/src/js/social_media_oauth.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}