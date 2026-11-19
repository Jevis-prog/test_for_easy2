from fastapi import HTTPException
from app.services.campaigns import CampaignCreate, create_campaign


class Client:
    def __init__(self, fail_stream=False):
        self.calls = []
        self.fail_stream = fail_stream
    def get(self, path):
        self.calls.append(('get', path))
        return {'id': 8}
    def put(self, path, data):
        self.calls.append(('put', path, data))
        return {"id": 7, "state": data["state"]}
    def post(self, path, data):
        self.calls.append(('post', path, data))
        if path == '/campaigns':
            return {'id': 7, 'name': data['name']}
        if path == '/streams' and self.fail_stream:
            raise HTTPException(502, 'failure')
        return {'id': 10}


def test_create_order_and_safe_partial_failure():
    data = CampaignCreate(name='Test', geo='au', offer_id=8, domain_id=1, group_id=2, traffic_source_id=3)
    client = Client()
    create_campaign(client, data)
    posts = [x for x in client.calls if x[0] == 'post']
    assert posts[0][2]['state'] == 'disabled'
    assert posts[1][2]['filters'][0]['payload'] == ['AU']
    assert posts[2][2]['offers'][0]['offer_id'] == 8
    assert client.calls[-1] == ('put', '/campaigns/7', {'state': 'active'})
    broken = Client(fail_stream=True)
    try:
        create_campaign(broken, data)
        assert False
    except HTTPException as exc:
        assert '#7' in exc.detail
        assert not any(call[0] == 'put' for call in broken.calls)


def test_campaign_configuration_matches_spec():
    data = CampaignCreate(name='Example', geo='AU', offer_id=8, domain_id=11, group_id=12, traffic_source_id=13)
    client = Client()
    create_campaign(client, data)
    posts = [call for call in client.calls if call[0] == 'post']
    campaign, google, offers = (posts[i][2] for i in range(3))
    assert (campaign['name'], campaign['domain_id'], campaign['group_id'], campaign['traffic_source_id'], campaign['type']) == ('Example', 11, 12, 13, 'position')
    assert google['type'] == 'regular' and google['position'] == 1
    assert google['schema'] == 'redirect' and google['action_type'] == 'http'
    assert google['action_payload'] == 'https://google.com'
    assert google['filters'] == [{'name': 'country', 'mode': 'accept', 'payload': ['AU']}]
    assert offers['type'] == 'default' and offers['position'] == 2 and offers['schema'] == 'landings'
    assert offers['offers'] == [{'offer_id': 8, 'share': 100, 'state': 'active'}]
