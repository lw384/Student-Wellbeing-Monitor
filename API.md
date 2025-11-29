## API

### upload csv

Description: read csv file and add into database

| URL                         | request | version | status |
| :-------------------------- | :------ | :------ | :----- |
| /services/upload_service.py | POST    | 1.0     |        |

#### Parameters

| Parameters | Type   | Required | Description | Example |
| :--------- | :----- | :------- | :---------- | :------ |
| username   | String | true     | 登录用户名  | carozhu |
| password   | String | true     | 登录密码    | 123456  |

#### Return

| Return       | Type    | Description |
| :----------- | :------ | :---------- |
| responseCode | Integer | 200：成功   |
| accessToken  | String  | 用户token   |
| ...          | ...     | ...         |

### 获取wellbeing总体均值

#### Parameters

| Parameters | Type   | Required | Description | Example |
| :--------- | :----- | :------- | :---------- | :------ |
| start week | String | true     | 登录用户名  | carozhu |
| End week   | String | true     | 登录密码    | 123456  |
| Module     |        |          |             |         |

#### Return

| Return           | Type    | Description |
| :--------------- | :------ | :---------- |
| Average sleep    | Integer | 5           |
| Average stress   | String  | 3           |
| Average response | ...     | 89%         |

### 获取wellbeing折线图

#### Parameters

| Parameters | Type   | Required | Description | Example |
| :--------- | :----- | :------- | :---------- | :------ |
| start week | String | true     | 登录用户名  | carozhu |
| End week   | String | true     | 登录密码    | 123456  |
| Module     |        |          |             |         |

#### Return

| Return | Type  | Description |
| :----- | :---- | :---------- |
| x      | Array | 5           |
| y      | Array |             |
|        |       |             |