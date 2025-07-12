
from odoo import models, fields

class SocialPost(models.Model):
    _name = 'social.post'
    _description = 'Social Media Post'

    name = fields.Char('Post Title')
    content = fields.Text('Content')
