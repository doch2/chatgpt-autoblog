import requests
import base64
import json
from random import randrange
from dotenv import load_dotenv
import os
import time
import shutil
from multiprocessing import Process
from tqdm import tqdm



load_dotenv(verbose=True, dotenv_path=".env")
time.sleep(1) #환경변수 로드를 위한 딜레이



def getBlogAuthHeader():
    user = os.getenv("WORDPRESS_USERNAME")
    password = os.getenv("WORDPRESS_PASSWORD")
    credentials = user + ':' + password
    token = base64.b64encode(credentials.encode())
    header = {"Authorization": "Basic " + token.decode("utf-8")}
    
    return header

def getTagData(authHeader):
    result = {}
    
    print("태그 데이터를 가져오는 중입니다...")
    for pageNum in tqdm(range(1, 27)):
        url = f"https://variousinfo.site/wp-json/wp/v2/tags?per_page=100&page={pageNum}"
        responce = requests.get(url, headers=authHeader)
        jsonData = json.loads(responce.content)

        for tag in jsonData:
            result[tag['id']] = tag['name']


    return result

def getPostDataList(authHeader, pageNum):
    url = f"https://variousinfo.site/wp-json/wp/v2/posts/?per_page=100&page={pageNum}"
    responce = requests.get(url, headers=authHeader)
    
    return json.loads(responce.content)

def addFeaturedImageInPost(authHeader, postID, imageID):
    url = f"https://variousinfo.site/wp-json/wp/v2/posts/{postID}"
    responce = requests.post(url, headers=authHeader, json={'featured_media': imageID})

def uploadPhotoToBlog(authHeader, tag, threadNum):
    media = {'file': open(f"{threadNum}_temp_image.jpg", "rb"),'caption': tag}
    responce = requests.post("https://variousinfo.site/wp-json/wp/v2/media", headers=authHeader, files = media)
    
    return json.loads(responce.content)['id']


def downloadPixabayImageAboutTopic(keyword, threadNum):
    url = "https://pixabay.com/api/"
    responce = requests.get(url, params={
        'key': os.getenv("PIXABAY_API_KEY"),
        'q': keyword,
        'image_type': 'photo',
        'per_page': 200
    })

    imageList = json.loads(responce.content)['hits']
    imageIndex = randrange(len(imageList))
    imageURL = imageList[imageIndex]['webformatURL']

    resp = requests.get(imageURL, stream=True)
    local_file = open(f"{threadNum}_temp_image.jpg", 'wb')
    resp.raw.decode_content = True
    shutil.copyfileobj(resp.raw, local_file)
    del resp


    return imageURL



def work(id, pageNumList, authHeader, tagData):
    for pageNum in pageNumList:
        postDataList = getPostDataList(authHeader, pageNum)
        
        for postData in tqdm(postDataList):
            print(f"이미지 등록 중인 게시글 이름: {postData['title']['rendered']}")

            postTagList = postData['tags']

            imageUploaded = False
            for postTagID in postTagList:
                try:
                    topic = tagData[postTagID]
                    downloadPixabayImageAboutTopic(topic, id)
                except:
                    continue
                else:
                    try:
                        imageID = uploadPhotoToBlog(authHeader, topic, id)
                        addFeaturedImageInPost(authHeader, postData['id'], int(imageID))
                        imageUploaded = True
                    except:
                        print("서버 등록 과정에서 이미지 등록 실패")
                        continue
                    finally:
                        break  
            
            if imageUploaded == False:
                print("적절한 이미지를 찾지 못해 이미지 등록 실패")



if __name__ == "__main__":
    authHeader = getBlogAuthHeader()
    tagData = getTagData(authHeader)

    print("태그 데이터 가져오기 완료")
    print("이미지 등록 시작")
    th1 = Process(target=work, args=(1, range(1,3), authHeader, tagData))
    th2 = Process(target=work, args=(2, range(3,6), authHeader, tagData))
    th3 = Process(target=work, args=(3, range(6,8), authHeader, tagData))
    th4 = Process(target=work, args=(4, range(7,11), authHeader, tagData))
    
    th1.start()
    th2.start()
    th3.start()
    th4.start()
    th1.join()
    th2.join()
    th3.join()
    th4.join()