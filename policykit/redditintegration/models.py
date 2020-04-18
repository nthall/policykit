from django.db import models
from policyengine.models import Community, CommunityUser, CommunityAction
from django.contrib.auth.models import Permission, ContentType, User
from policykit.settings import REDDIT_CLIENT_SECRET
import urllib
from urllib import parse
import base64
import json
import logging

logger = logging.getLogger(__name__)


REDDIT_USER_AGENT = 'PolicyKit:v1.0 (by /u/axz1919)'

REDDIT_ACTIONS = []

# Create your models here.


def refresh_access_token(refresh_token):
    data = parse.urlencode({
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
        }).encode()
        
    req = urllib.request.Request('https://www.reddit.com/api/v1/access_token', data=data)
    
    credentials = ('%s:%s' % ('QrZzzkLgVc1x6w', REDDIT_CLIENT_SECRET))
    encoded_credentials = base64.b64encode(credentials.encode('ascii'))

    req.add_header("Authorization", "Basic %s" % encoded_credentials.decode("ascii"))
    req.add_header("User-Agent", "PolicyKit-App-Reddit-Integration v 1.0")

    resp = urllib.request.urlopen(req)
    res = json.loads(resp.read().decode('utf-8'))
    return res


class RedditCommunity(Community):
    API = 'https://oauth.reddit.com/'
    
    team_id = models.CharField('team_id', max_length=150, unique=True)

    access_token = models.CharField('access_token', 
                                    max_length=300, 
                                    unique=True)
    
    refresh_token = models.CharField('refresh_token', 
                               max_length=500, 
                               null=True)
    
    def make_call(self, url, values=None):
        logger.info(self.API + url)
        try:
            req = urllib.request.Request(self.API + url)
            req.add_header('Authorization', 'bearer %s' % self.access_token)
            req.add_header("User-Agent", REDDIT_USER_AGENT)
            
            logger.info(req.headers)
            
            resp = urllib.request.urlopen(req)
            res = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.reason == 'Unauthorized':
                self.refresh_access_token()
                
                req = urllib.request.Request(self.API + url)
                req.add_header('Authorization', 'bearer %s' % self.access_token)
                req.add_header("User-Agent", REDDIT_USER_AGENT)
                resp = urllib.request.urlopen(req)
                res = json.loads(resp.read().decode('utf-8'))
            else:
                logger.info(e)
        logger.info(res)
        return res
    
    def refresh_access_token(self):
        res = refresh_access_token(self.refresh_token)
        self.access_token = res['access_token']
        self.save()

    
    def notify_action(self, action, policy, users, post_type='channel', template=None, channel=None):
        from redditintegration.views import post_policy
        post_policy(policy, action, users, post_type, template, channel)
    
    def save(self, *args, **kwargs):      
        super(RedditCommunity, self).save(*args, **kwargs)
        
        content_types = ContentType.objects.filter(model__in=REDDIT_ACTIONS)
        perms = Permission.objects.filter(content_type__in=content_types, name__contains="can add ")
        for p in perms:
            self.base_role.permissions.add(p)
            

    def execute_community_action(self, action, delete_policykit_post=True):
        from policyengine.models import LogAPICall, CommunityUser
        from policyengine.views import clean_up_proposals
        
        logger.info('here')
        
        logger.info(action)
        
#         obj = action
#         
#         if not obj.community_origin or (obj.community_origin and obj.community_revert):
#             logger.info('EXECUTING ACTION BELOW:')
#             call = self.API + obj.ACTION
#             logger.info(call)
#         
#             
#             obj_fields = []
#             for f in obj._meta.get_fields():
#                 if f.name not in ['polymorphic_ctype',
#                                   'community',
#                                   'initiator',
#                                   'communityapi_ptr',
#                                   'communityaction',
#                                   'communityactionbundle',
#                                   'community_revert',
#                                   'community_origin',
#                                   'is_bundled'
#                                   ]:
#                     obj_fields.append(f.name) 
#             
#             data = {}
#             
#             if obj.AUTH == "user":
#                 data['token'] = action.proposal.author.access_token
#                 if not data['token']:
#                     admin_user = CommunityUser.objects.filter(is_community_admin=True)[0]
#                     data['token'] = admin_user.access_token
#             elif obj.AUTH == "admin_bot":
#                 if action.proposal.author.is_community_admin:
#                     data['token'] = action.proposal.author.access_token
#                 else:
#                     data['token'] = community.access_token
#             elif obj.AUTH == "admin_user":
#                 admin_user = CommunityUser.objects.filter(is_community_admin=True)[0]
#                 data['token'] = admin_user.access_token
#             else:
#                 data['token'] = self.access_token
#                 
#             
#             for item in obj_fields:
#                 try :
#                     if item != 'id':
#                         value = getattr(obj, item)
#                         data[item] = value
#                 except obj.DoesNotExist:
#                     continue
#     
#             res = LogAPICall.make_api_call(self, data, call)
#             
#             
#             # delete PolicyKit Post
#             if delete_policykit_post:
#                 posted_action = None
#                 if action.is_bundled:
#                     bundle = action.communityactionbundle_set.all()
#                     if bundle.exists():
#                         posted_action = bundle[0]
#                 else:
#                     posted_action = action
#                     
#                 if posted_action.community_post:
#                     admin_user = CommunityUser.objects.filter(is_community_admin=True)[0]
#                     values = {'token': admin_user.access_token,
#                               'ts': posted_action.community_post,
#                               'channel': obj.channel
#                             }
#                     call = self.API + 'chat.delete'
#                     _ = LogAPICall.make_api_call(self, values, call)
#     
#             
#             
#             if res['ok']:
#                 clean_up_proposals(action, True)
#             else:
#                 error_message = res['error']
#                 logger.info(error_message)
#                 clean_up_proposals(action, False)
#     
#         else:
#             clean_up_proposals(action, True)
            

class RedditUser(CommunityUser):
    refresh_token = models.CharField('refresh_token', 
                               max_length=500, 
                               null=True)
    
    avatar = models.CharField('avatar', 
                           max_length=500, 
                           null=True)
    
    def make_call(self, url, values=None):
        logger.info(url)
        req = urllib.request.Request(self.community.API + url)
        req.add_header('Authorization', 'bearer %s' % self.access_token)
        req.add_header("User-Agent", REDDIT_USER_AGENT)
        resp = urllib.request.urlopen(req)
        res = json.loads(resp.read().decode('utf-8'))
        logger.info(res)
        return res
    
    def refresh_access_token(self):
        res = refresh_access_token(self.refresh_token)
        self.access_token = res['access_token']
        self.save()
    
    def save(self, *args, **kwargs):      
        super(RedditUser, self).save(*args, **kwargs)
        group = self.community.base_role
        group.user_set.add(self)


class RedditMakePost(CommunityAction):
    ACTION = 'api/submit'
    AUTH = 'user'
    
    title = models.CharField('title', 
                               max_length=500, 
                               null=True)
    text = models.TextField()
    
    kind = models.CharField('kind', 
                               max_length=30, 
                               default="self")
    
    name = models.CharField('name', 
                               max_length=100, 
                               null=True)
    
    class Meta:
        permissions = (
            ('can_execute', 'Can execute reddit make post'),
        )

    
    def revert(self):
        values = {'id': self.name
                }
        super().revert(values, 'api/remove')
        

