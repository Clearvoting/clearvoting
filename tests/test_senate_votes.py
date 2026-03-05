import pytest
from app.services.senate_votes import parse_senate_vote_xml, SenateVoteService

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<roll_call_vote>
  <congress>119</congress>
  <session>2</session>
  <vote_number>44</vote_number>
  <vote_date>March 2, 2026</vote_date>
  <vote_question_text>On Cloture on the Motion to Proceed</vote_question_text>
  <vote_document_text>H.R. 6644</vote_document_text>
  <vote_result_text>Agreed to</vote_result_text>
  <vote_title>A bill to increase the supply of housing in America</vote_title>
  <count>
    <yeas>84</yeas>
    <nays>6</nays>
    <present>1</present>
    <absent>9</absent>
  </count>
  <members>
    <member>
      <member_full>Alsobrooks (D-MD)</member_full>
      <first_name>Angela</first_name>
      <last_name>Alsobrooks</last_name>
      <party>D</party>
      <state>MD</state>
      <vote_cast>Yea</vote_cast>
      <lis_member_id>S428</lis_member_id>
    </member>
    <member>
      <member_full>Johnson (R-WI)</member_full>
      <first_name>Ron</first_name>
      <last_name>Johnson</last_name>
      <party>R</party>
      <state>WI</state>
      <vote_cast>Nay</vote_cast>
      <lis_member_id>S345</lis_member_id>
    </member>
    <member>
      <member_full>Sanders (I-VT)</member_full>
      <first_name>Bernie</first_name>
      <last_name>Sanders</last_name>
      <party>I</party>
      <state>VT</state>
      <vote_cast>Yea</vote_cast>
      <lis_member_id>S313</lis_member_id>
    </member>
  </members>
</roll_call_vote>
"""


def test_parse_vote_metadata():
    result = parse_senate_vote_xml(SAMPLE_XML)
    assert result["congress"] == 119
    assert result["session"] == 2
    assert result["vote_number"] == 44
    assert result["question"] == "On Cloture on the Motion to Proceed"
    assert result["result"] == "Agreed to"
    assert result["document"] == "H.R. 6644"


def test_parse_vote_counts():
    result = parse_senate_vote_xml(SAMPLE_XML)
    assert result["counts"]["yeas"] == 84
    assert result["counts"]["nays"] == 6
    assert result["counts"]["present"] == 1
    assert result["counts"]["absent"] == 9


def test_parse_member_votes():
    result = parse_senate_vote_xml(SAMPLE_XML)
    assert len(result["members"]) == 3

    yea = result["members"][0]
    assert yea["last_name"] == "Alsobrooks"
    assert yea["party"] == "D"
    assert yea["state"] == "MD"
    assert yea["vote"] == "Yea"

    nay = result["members"][1]
    assert nay["last_name"] == "Johnson"
    assert nay["vote"] == "Nay"

    ind = result["members"][2]
    assert ind["party"] == "I"
    assert ind["vote"] == "Yea"


def test_build_url():
    from unittest.mock import MagicMock
    service = SenateVoteService(cache=MagicMock())
    url = service._build_url(119, 2, 44)
    assert "vote1192" in url
    assert "vote_119_2_00044.xml" in url
