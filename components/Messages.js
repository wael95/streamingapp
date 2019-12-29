import * as React from 'react';
import { Text, View, StyleSheet } from 'react-native';
import { Constants } from 'expo';
import {
  Container,
  Content,
  Header,
  List,
  ListItem,
  Left,
  Right,
  Icon,
  Thumbnail,
  Body,
} from 'native-base';

import MessageListItem from './MessageListItem';
export default class Messages extends React.Component {
  render() {
    return (
      <Container style={styles.container}>
        <Header>
          <Text style={styles.paragraph}>Chats</Text>
        </Header>
        <Content>
          <List>
            <MessageListItem
              photo={require('../assets/Profiles/pexels-photo-220453.jpeg')}
              name="semi javian"
            />
            <MessageListItem
              photo={require('../assets/Profiles/pexels-photo-1239291.jpeg')}
              name="Nathali Kareem"
            />
            <MessageListItem
              photo={require('../assets/download.jpg')}
              name="Kamal zimar"
            />
            <MessageListItem
              photo={require('../assets/Profiles/pexels-photo-774909.jpeg')}
              name="Helen Rakhteev"
            />
            <MessageListItem
              photo={require('../assets/Profiles/pexels-photo-774095.jpeg')}
              name="Javla Vita"
            />
            <MessageListItem
              photo={require('../assets/Profiles/pexels-photo-736716.jpeg')}
              name="Tum La'a"
            />
          </List>
        </Content>
      </Container>
    );
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: Constants.statusBarHeight,
  },
  paragraph: {
    fontSize:35,
    fontWeight: 'bold',
    color: 'black',
  },
});
