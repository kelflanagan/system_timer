from __future__ import print_function

import aws
import myspace
import string

""" delete_resources() deletes all of the aws resources associated with this
service.
parameters: resource_path
            function_name (includes namespaced prefix added at install)
returns: True on success and False on failure
"""
def delete_resources(resource_path, service_name):
    # delete assocaited lambda function
    if not myspace.delete_lambda(service_name):
        print('failed to delete lambda function {}'.format(service_name))
            
    # delete SNS services
    sns_name = string.split(service_name, '_')[0] + '_' + '1_Minute'
    if not myspace.delete_sns(sns_name):
        print('failed to delete SNS topic {}'.format(sns_name))
    sns_name = string.split(service_name, '_')[0] + '_' + '5_Minute'
    if not myspace.delete_sns(sns_name):
        print('failed to delete SNS topic {}'.format(sns_name))

    # delete dynamoDB services
    if not myspace.delete_dynamodb(service_name):
        print('failed to delete dynamoDB table {}'.format(service_name))

    # delete API resource
    api_name = string.split(service_name, '_')[0]
    if not myspace.delete_resource(api_name, resource_path):
        print('failed to delete API resource {}'.format(resource_path))
        
    return True


def system_timer(event, context):
    # determine how we were invoked
    # test to see if called via API
    if 'resource_path' in event:
        # called by system_timer API, react to HTTP methods
        if event['http_method'] == 'GET':
            # get state from dynamoDB and return
            state = myspace.get_service_state(context.function_name)
            if state != None:
                del state['state']
                return state
            else:
                raise Exception('Server Error')
        
        elif event['http_method'] == 'PUT':
            if 'minutes' not in event:
                raise Exception('Server Error')
            else:
                if not myspace.update_service_state(context.function_name, 'minutes', str(event['minutes']), 'N'):
                    raise Exception('Server Error')
            return
        
        elif event['http_method'] == 'DELETE':
            success = delete_resources(
                event['resource_path'],
                context.function_name
                )
            if success:
                return
            else:
                raise Exception('Server Error')

        else:
            raise Exception('MethodNotAllowed')

    else:
        state = myspace.get_service_state(context.function_name)
        if state != None:
            minutes_since_beginning = state['minutes']
        else:
            print('system_timer(): Error retrieving state')
            return

        # increment minutes entry indicating
        # another minute has passed
        minutes_since_beginning += 1
        success = myspace.update_service_state(
            context.function_name, 
            'minutes', 
            str(minutes_since_beginning), 
            'N'
            )
        if not success:
            print('system_timer(): Error updating state')
            return

        # send event_message to the 1_Minute event bus
        event_message = '{"minutes" : ' + str(minutes_since_beginning) + '}'
        success = myspace.raise_event(
            context.function_name, 
            '1_Minute', 
            event_message, 
            '1_Minute'
            )
        if not success:
            print('system_timer(): Failed raising 1_Minute event')
            return

        # determine if it is time for other time events
        # 5 minute event
        if minutes_since_beginning % 5 == 0:
            # send event_message to the 5_Minute event bus
            success = myspace.raise_event(
                context.function_name, 
                '5_Minute', 
                event_message, 
                '5_Minute'
                )
            if not success:
                print('system_timer(): Failed raising 5_Minute event')
                return

        return
