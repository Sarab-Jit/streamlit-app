import requests as r
import pandas as pd
import os
import time
from json import dumps
import streamlit as st

st.set_page_config(
    page_title="•ᴗ•",     # Browser tab shows only 🐽
    page_icon='stick.jpg',      # No extra emoji favicon
    layout="wide",
    initial_sidebar_state="expanded"
)

dcr_data = {
      'Created Date(CRM)' : None,
      'Submitted by' : None,
      'Territory' : None,
      'Veeva Id' : None,
      'NPI' : None,
      'First Name' : None,
      'Last Name' : None,
      'Address' : None,
      'City' : None,
      'State' : None,
      'Zip' : None,
      'Task Id' : None,
      'User Id' : None,
      'Account Id' : None
      }




creds = {'username' : None,
  'password' : None,
  'domain' : None,
  'api_version' : 'v25.2'
}

#Authentication -- takes creds and authenticates in vault
def authenticate(org_details: dict):
  '''
   Adds/ Updates the session id to the provided dict
   '''
  if 'username' not in org_details or  'password' not in org_details or 'domain' not in org_details or 'api_version' not in org_details:
    raise Exception(f'Org details are missing :{org_details}')

  domain = org_details['domain']
  api_version = org_details['api_version']
  username = org_details['username']
  password = org_details['password']

  url = f'{domain}/api/{api_version}/auth'
  u_data = {'username': username, 'password': password}
  resp = r.post(url, data = u_data)
  resp.raise_for_status()
  
  if resp.json()['responseStatus'] != 'SUCCESS':
    return False, resp.json()
  org_details['session_id'] = resp.json().get('sessionId')
  return True, resp.json()

def get_data(org_details: dict, dcr,dcr_data):
  dcr_data['Task Id'] = dcr

  domain = org_details['domain']
  api_version = org_details['api_version']

  if 'session_id' not in org_details:
    raise Exception(f'Session Id is missing')
  session_id = org_details['session_id']
  headers = {'Authorization': f'Bearer {session_id}'}
  url = f'{domain}/api/{api_version}/query'
  # This fetches   Created Date, User name ,  Task Id, User Id and Account Id
  first_query = {
      'q':f"""
              SELECT created_date__v,
              created_by__v,
              ownerid__vr.name__v,
              account__v

              FROM  data_change_request__v
                  where
                  dcr_external_id__v = {dcr_data['Task Id']}

                  """}
  resp1 = r.post(url, headers = headers, data = first_query)
  if resp1.json()['responseStatus'] != 'SUCCESS' and resp1.json()['responseStatus'] != 'WARNING':
    raise Exception(dumps(resp1.json(),indent = 4))
  if resp1.json()['responseDetails']['total'] != 1:
    raise Exception(f"Row count from the query {first_query['q']} is not 1")
  dcr_resp = resp1.json()['data'][0]
  dcr_data['Created Date(CRM)'] = dcr_resp['created_date__v'][:10]
  dcr_data['Submitted by'] = dcr_resp['ownerid__vr.name__v']
  dcr_data['User Id'] = dcr_resp['created_by__v']
  dcr_data['Account Id'] = dcr_resp['account__v']


  # This fetches the users territory
  second_query = {
      'q' : f"""
      select
      territory__vr.name__v,
      user__v
      from user_territory__v
      where
      user__v = '{dcr_data['User Id']}'
      """
  }
  resp2 = r.post(url, headers = headers, data = second_query)
  if resp2.json()['responseStatus'] != 'SUCCESS' and resp2.json()['responseStatus'] != 'WARNING':
    raise Exception(dumps(resp2.json(),indent = 4))
  if resp2.json()['responseDetails']['total'] != 1:
    raise Exception(f"Row count from the query {second_query['q']} is not 1")
  dcr_resp = resp2.json()['data'][0]
  dcr_data['Territory'] = dcr_resp['territory__vr.name__v']

  # This fetches account details like veeva id, npi, first name, last name
  third_query = {
      'q' : f"""
      select
      id,
      veeva_network_id__v,
      npi__v,
      first_name_cda__v,
      last_name_cda__v
      from account__v
      where
      id = '{dcr_data['Account Id']}'
      """
  }
  resp3 = r.post(url, headers = headers, data = third_query)
  if resp3.json()['responseStatus'] != 'SUCCESS' and resp3.json()['responseStatus'] != 'WARNING':
    raise Exception(dumps(resp3.json(),indent=4))
  if resp3.json()['responseDetails']['total'] != 1:
    raise Exception(f"Row count from the query {third_query['q']} is not 1")
  dcr_resp = resp3.json()['data'][0]
  dcr_data['Veeva Id'] = dcr_resp['veeva_network_id__v']
  dcr_data['NPI'] = dcr_resp['npi__v']
  dcr_data['First Name'] = dcr_resp['first_name_cda__v']
  dcr_data['Last Name'] = dcr_resp['last_name_cda__v']
  #
  if dcr_data['Territory'][0] == 'A':
    fourth_query = {
      'q' : f"""
      SELECT
      name__v,
      city_cda__v,
      state_province__v,
      postal_code_cda__v,
      coll_current_ic_address_adhd__c,
      coll_current_ic_address_pain__c,
      primary_cda__v
      FROM address__v
      where account__v= '{dcr_data['Account Id']}'
      and coll_current_ic_address_adhd__c = 'true'
      """
  }
  elif dcr_data['Territory'][0] == 'R':
    fourth_query = {
      'q' : f"""
      SELECT
      name__v,
      city_cda__v,
      state_province__v,
      postal_code_cda__v,
      coll_current_ic_address_adhd__c,
      coll_current_ic_address_pain__c,
      primary_cda__v
      FROM address__v
      where account__v= '{dcr_data['Account Id']}'
      and coll_current_ic_address_pain__c = 'true'
      """
  }
  else:
    fourth_query = {
      'q' : f"""
      SELECT
      name__v,
      city_cda__v,
      state_province__v,
      postal_code_cda__v,
      coll_current_ic_address_adhd__c,
      coll_current_ic_address_pain__c,
      primary_cda__v
      FROM address__v
      where account__v= '{dcr_data['Account Id']}'
      and primary_cda__v = 'true'
      """
  }

  resp4 = r.post(url, headers = headers, data = fourth_query)
  if resp4.json()['responseStatus'] != 'SUCCESS' and resp4.json()['responseStatus'] != 'WARNING':
    raise Exception(dumps(resp4.json(),indent=4))
  if resp4.json()['responseDetails']['total'] != 1:
    raise Exception(f"Row count from the query {fourth_query['q']} is not 1")
  dcr_resp = resp4.json()['data'][0]
  dcr_data['Address'] = dcr_resp['name__v']
  dcr_data['City'] = dcr_resp['city_cda__v']
  dcr_data['State'] = dcr_resp['state_province__v'][0][:2].upper()
  dcr_data['Zip'] = dcr_resp['postal_code_cda__v']
  return




if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if 'creds' not in st.session_state:
   st.session_state.creds = creds

st.title("Pending DCRs or something :D ")

def login_form():
    with st.form("login_form"):
        domain = st.text_input("Vault Domain")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted and domain and username and password:
            st.session_state.creds["username"] = username
            st.session_state.creds["password"] = password
            st.session_state.creds["domain"] = f"https://{domain}"

            try:
                success, res = authenticate(st.session_state.creds)
                if success:
                    st.session_state.logged_in = True
                    st.success("Login successful ✅")
                    st.rerun()
                else:
                    st.error(f"Login failed ❌:\n{dumps(res, indent=4)}")
            except Exception as e:
                st.error(f"Login failed ❌: {e}")

def main():
  global dcr_data
  if "dcr_data" not in st.session_state:
        st.session_state.dcr_data = dcr_data

      
  
  dcr_id = st.text_input("Enter the DCR ID: ")
  dcr_id = dcr_id.strip()
  if st.button('Fetch DCR Data :('):
    if len(dcr_id) != 18:
       st.warning('Please enter a valid DCR ID')
    else:
      try:
        get_data(org_details=st.session_state.creds,dcr= dcr_id,dcr_data = st.session_state.dcr_data)
        st.write("✅ Data fetched successfully")
        dcr_for_copy = f'' 
      
      except Exception as e:
        st.error(f"❌ Data fetch failed: {e}")

  st.write(st.session_state.dcr_data)
  fields_order = [
    'Created Date(CRM)',
    'Submitted by',
    'Territory',
    'Veeva Id',
    'NPI',
    'First Name',
    'Last Name',
    'Address',
    'City',
    'State',
    'Zip',
    'Task Id'
]
  dcr_to_copy = '$'.join(str(st.session_state.dcr_data[field]) for field in fields_order)
  st.code(dcr_to_copy)

if not st.session_state.logged_in:
    login_form()
else:

    main()




