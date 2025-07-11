from odoo import models, fields, api


class SocialMediaProfile(models.Model):
    _name = 'social_media.profile'
    _description = 'Social Media Profile'
    _order = 'display_name'
    
    account_id = fields.Many2one(
        'social_media.account',
        string='Account',
        required=True,
        ondelete='cascade'
    )
    external_profile_id = fields.Char(
        string='External Profile ID',
        required=True
    )
    username = fields.Char(string='Username')
    display_name = fields.Char(string='Display Name')
    profile_type = fields.Selection([
        ('following', 'Following'),
        ('follower', 'Follower'),
    ], string='Profile Type', default='following')
    profile_metadata = fields.Json(
        string='Profile Metadata',
        help='Additional profile information (bio, profile pic, etc.)'
    )
    last_fetched = fields.Datetime(string='Last Fetched')
    
    # Related fields
    service = fields.Selection(
        related='account_id.service',
        string='Service',
        store=True,
        readonly=True
    )
    user_id = fields.Many2one(
        related='account_id.user_id',
        string='User',
        store=True,
        readonly=True
    )
    
    # Relations
    post_ids = fields.One2many(
        'social_media.post',
        'profile_id',
        string='Posts'
    )
    
    post_count = fields.Integer(
        string='Post Count',
        compute='_compute_post_count'
    )
    
    _sql_constraints = [
        ('unique_profile_per_account',
         'UNIQUE(account_id, external_profile_id)',
         'Profile ID must be unique per account!')
    ]
    
    @api.depends('post_ids')
    def _compute_post_count(self):
        for profile in self:
            profile.post_count = len(profile.post_ids)
    
    def name_get(self):
        result = []
        for profile in self:
            if profile.display_name and profile.username:
                name = f"{profile.display_name} (@{profile.username})"
            elif profile.username:
                name = f"@{profile.username}"
            elif profile.display_name:
                name = profile.display_name
            else:
                name = f"Profile {profile.external_profile_id}"
            result.append((profile.id, name))
        return result
    
    def action_view_posts(self):
        """Open a view showing all posts from this profile"""
        self.ensure_one()
        return {
            'name': f'Posts from {self.display_name or self.username}',
            'type': 'ir.actions.act_window',
            'res_model': 'social_media.post',
            'view_mode': 'tree,form',
            'domain': [('profile_id', '=', self.id)],
            'context': {
                'default_profile_id': self.id,
                'default_account_id': self.account_id.id,
            }
        }