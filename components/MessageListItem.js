import * as React from 'react';
import { Text } from 'react-native';
import {
  List,
  ListItem,
  Left,
  Right,
  Icon,
  Thumbnail,
  Body,
} from 'native-base';

export default class MessageListItem extends React.Component {
  render() {
    return (
      <ListItem
        style={{ justifyCotent: 'center', borderColor: 'transparent' }}
        avatar>
        <Left style={{ borderColor: 'transparent' }}>
          <Thumbnail source={this.props.photo} />
        </Left>
        <Body style={{ borderColor: 'transparent' }}>
          <Text
            style={{
              fontWeight: 'bold',
              color: 'black',
            }}>
            {this.props.name}
          </Text>
        </Body>
        <Right style={{ borderColor: 'transparent', justifyContent: 'center' }}>
          <Icon name="arrow-forward" />
        </Right>
      </ListItem>
    );
  }
}
