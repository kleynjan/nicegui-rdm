from muezzin.models import MuezzinGroup, MuezzinGroupMembership, MuezzinMessage, MuezzinReminderMessage
from qiaa.models import Account, Quser, Qgroup, QuserQgroup, qAuditEntry

account = Account.objects.get(subdomain='rdgg')
msgs = MuezzinMessage.objects.active_for_account(account).filter(pk=id)

account = Account.objects.get(subdomain='rdgg')
msg = MuezzinMessage.objects.get(pk=1762)
# msg = msgs[0]
group = msg.group
if group.is_all_group:
    pass
    # empty and refill the "all" group...
MuezzinGroupMembership.objects.filter(group=group).delete()
inner = MuezzinGroupMembership.objects.active_for_account(account).values('member__dj_user').query  # dj_users in 1 or more groups
all_users = Quser.objects.active_for_account(account).filter(
    dj_user__in=inner).exclude(
        username__startswith='nood-')
for u in all_users:
    ms = MuezzinGroupMembership(member=u, group=group)
    ms.save()
