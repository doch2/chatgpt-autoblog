import openai
import requests
import base64
import re
import json
from random import randrange
from datetime import timedelta
from datetime import datetime
from dotenv import load_dotenv
import os
import time


load_dotenv(verbose=True, dotenv_path="/blog/environment.env")
time.sleep(1) #환경변수 로드를 위한 딜레이
openai.api_key = os.getenv("OPENAI_API_KEY")


def getChatGPTResult(prompt):
    # 모델 엔진 선택
    model_engine = "text-davinci-003"

    # 맥스 토큰
    max_tokens = 2048

    # 블로그 생성
    completion = openai.Completion.create(
        engine=model_engine,
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=0.6,      # creativity
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return completion

def getBlogTopicList(topic):
    response = getChatGPTResult(f'Please recommend 35x blog topics related to {topic}.')
    pureData = response.choices[0].text.split('\n')

    pureData= [v for v in pureData if v] #빈 문자열 제거
    topicList = []
    for topic in pureData:
        topicList.append(topic[topic.index('.')+2:]) #앞에 목록 번호 제거
        

    return topicList

def extractionBlogPostHashTag(postContent):
    hashtag_pattern = r'(#+[a-zA-Z0-9(_)]{1,})'
    hashtags = [w[1:] for w in re.findall(hashtag_pattern, postContent)]
    tag_string = ""
    for w in hashtags:
        # 3글자 이상 추출
        if len(w) > 3:
            tag_string += f'{w}, '
    
    tag_string = re.sub(r'[^a-zA-Z, ]', '', tag_string)
    tag_string = tag_string.strip()[:-1]

    return (tag_string.split(', '))

def getBlogAuthHeader():
    user = os.getenv("WORDPRESS_USERNAME")
    password = os.getenv("WORDPRESS_PASSWORD")
    credentials = user + ':' + password
    token = base64.b64encode(credentials.encode())
    header = {"Authorization": "Basic " + token.decode("utf-8")}
    
    return header

def createPostInWordPress(authHeader, postContent):
    url = "https://variousinfo.site/wp-json/wp/v2/posts"
    responce = requests.post(url, headers=authHeader, json=postContent)

def getBlogCategoryData():
    url = "https://variousinfo.site/wp-json/wp/v2/categories"
    responce = requests.get(url)

    categoryNameList = []
    categoryIndexList = []

    for categoryData in json.loads(responce.content):
        #uncategorized 제거
        if categoryData['name'] != 'Uncategorized':
            categoryNameList.append(categoryData['name'])
            categoryIndexList.append(categoryData['id'])
    

    return categoryNameList, categoryIndexList

def getPostTagIdList(authHeader, tagNameList):
    url = "https://variousinfo.site/wp-json/wp/v2/tags"

    tagIndexList = []
    for tagName in tagNameList:
        responce = requests.post(
            url, 
            headers=authHeader, 
            json={
                'name': tagName
            }
        )

        if responce.status_code == 201: #태그가 존재하지 않았던 경우
            tagIndexList.append(json.loads(responce.content)['id'])
        elif responce.status_code == 400: #태그가 존재했던 경우
            tagIndexList.append(json.loads(responce.content)['data']['term_id'])


    return tagIndexList

def isDuplicationPostTopic(topic):
    url = "https://variousinfo.site/wp-json/wp/v2/posts"
    responce = requests.get(url)

    postTopicList = []
    for postData in json.loads(responce.content):
        postTopicList.append(postData['title']['rendered'])
    
    if topic in postTopicList:
        return True
    else:
        return False

def getPostRandomDate():
    start = datetime.strptime('1/1/2022 1:30 PM', '%m/%d/%Y %I:%M %p')
    end = datetime.strptime('1/31/2023 4:50 AM', '%m/%d/%Y %I:%M %p')

    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = randrange(int_delta)
    return (start + timedelta(seconds=random_second)).strftime("%Y-%m-%dT%H:%M:%S")


if __name__=="__main__":
    authHeader = getBlogAuthHeader()
    
    categoryNameList, categoryIndexList = getBlogCategoryData()

    for category in categoryNameList:
        topicList = getBlogTopicList(category)
        print(f"{category}의 Topic 리스트: {topicList}")

        for topic in topicList:
            if isDuplicationPostTopic(topic):
                print(f"{topic}는 중복된 Topic으로 포스팅을 진행하지 않습니다.")
                continue


            prompt = f'''
            Write blog posts in html format.
            Write the theme of your blog as "{topic}".
            Highlight, bold, or italicize important words or sentences.
            Please include the restaurant's address, menu recommendations and other helpful information(such as opening and closing hours) as a list style.
            Please make the blog readable for more than 10 minutes. The number of words in the blog must be at least 600 words.
            Please fill out the details about Topic.
            The audience of this article is 20-40 years old.
            Create several hashtags and add them only at the end of the line.
            Add a summary of the entire article at the beginning of the blog post.
            '''
            
            
            response = getChatGPTResult(prompt)
            postContent = response.choices[0].text

            createPostInWordPress(
                authHeader,
                {
                    'title'    : topic,
                    'status'   : 'publish', 
                    'content'  : postContent,
                    'categories': categoryIndexList[categoryNameList.index(category)],
                    'tags': ', '.join(map(str, getPostTagIdList(authHeader, extractionBlogPostHashTag(postContent)))),
                    'date'   : getPostRandomDate()
                }
            )

            print(f"{category}의 {topic} 생성 완료")

            time.sleep(180) #너무 빠른 생성을 막기위한 딜레이

