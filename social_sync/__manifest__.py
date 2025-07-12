
{
    'name': 'Social Media Sync',
    'version': '1.0',
    'summary': 'An example module to sync posts to social media.',
    'description': 'A simple custom module example for hackathon.',
    'author': 'Your Name',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/social_sync_views.xml',
    ],
    'installable': True,
    'application': True,
}
