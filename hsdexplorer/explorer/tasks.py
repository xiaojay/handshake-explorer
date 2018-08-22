from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.conf import settings
import redis

import explorer.history.write as hwrite
from . import hsd

REDIS_CLIENT = redis.Redis(host=settings.CELERY_REDIS_HOST, port=settings.CELERY_REDIS_PORT)


@shared_task
def process_next_block():
    """
    TODO:
    * Update to process multiple blocks at a time if behind
    """
    # Ignore the job if we are already processing another job like this
    lock = REDIS_CLIENT.lock('celery_process_next_block_lock', timeout=120, blocking_timeout=0)
    if not lock.acquire(blocking=False):
        return
    try:
        current_block_height = hwrite.get_max_block() + 1
        block = True
        while block:
            block = hsd.get_block(current_block_height)
            # Stop processing once we hit to max block
            if not block:
                return

            # Check if the new block is from a fork
            if block['prevBlock'] != hwrite.get_processed_block_hash(current_block_height - 1):
                print('Reverting block {} due to change'.format(current_block_height - 1))
                hwrite.unprocess_block(current_block_height - 1)
                current_block_height -= 1
                return

            # Process the new block
            with hwrite.datastore_client.transaction():
                for tx_index, tx in enumerate(block['txs']):
                    for event in tx['outputs']:
                        if event['action'] == 'NONE':
                            continue
                        event['tx_hash'] = tx['hash']
                        event['tx_index'] = tx_index
                        event['block'] = block['height']
                        print(current_block_height, event)
                        hwrite.insert(event)
                hwrite.mark_block(block['height'], block['hash'])
            print('Processed {}'.format(current_block_height))
            current_block_height += 1
    finally:
        lock.release()
